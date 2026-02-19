"""FTP/FTPS storage backend."""

from __future__ import annotations

import io
import posixpath
import ssl
from ftplib import FTP, FTP_TLS, error_perm

from file_tools.config.models import StorageConfig

from .base import NotSupportedError, StorageBackend, StorageEntry, StorageStat


def _clean_posix(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    norm = posixpath.normpath(path)
    if not norm.startswith("/"):
        norm = "/" + norm
    return norm


def _to_bool(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _to_int(value: str | None, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


class FtpStorage(StorageBackend):
    backend_name = "ftp"

    def __init__(self, storage: StorageConfig, *, timeout_s: int | None = None) -> None:
        cfg = storage.ftp
        if not cfg.host:
            raise ValueError("FTP storage requires ftp.host")
        self._host = cfg.host
        self._port = _to_int(cfg.port, 21)
        self._user = cfg.username or ""
        self._password = cfg.password if cfg.password is not None else str()
        self._base_dir = _clean_posix(cfg.base_dir or "/")
        self._use_tls = _to_bool(cfg.use_tls)

        insecure = _to_bool(storage.tls.insecure_skip_verify)
        self._ssl_context: ssl.SSLContext | None = None
        self._timeout_s = _to_int(str(timeout_s) if timeout_s is not None else None, 30)
        if self._use_tls:
            ctx = ssl.create_default_context()
            if insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            elif storage.tls.ca_bundle_path:
                ctx.load_verify_locations(cafile=storage.tls.ca_bundle_path)
            self._ssl_context = ctx

    def _connect(self) -> FTP:
        if self._use_tls:
            ftp: FTP | FTP_TLS = FTP_TLS(context=self._ssl_context)
        else:
            ftp = FTP()
        ftp.connect(self._host, self._port, timeout=self._timeout_s)
        ftp.login(self._user, self._password)
        if self._use_tls and isinstance(ftp, FTP_TLS):
            ftp.prot_p()
        # Always start from base_dir to keep path mapping consistent.
        if self._base_dir and self._base_dir != "/":
            ftp.cwd(self._base_dir)
        return ftp

    def _remote_path(self, path: str) -> str:
        rel = _clean_posix(path).lstrip("/")
        if not rel:
            return self._base_dir
        if self._base_dir == "/":
            return "/" + rel
        return posixpath.join(self._base_dir, rel)

    def read_bytes(self, path: str) -> bytes:
        remote = self._remote_path(path)
        ftp = self._connect()
        try:
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {remote}", buf.write)
            return buf.getvalue()
        except error_perm as exc:
            # Common "550" for not found.
            if str(exc).startswith("550"):
                raise FileNotFoundError(path) from exc
            raise
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        remote = self._remote_path(path)
        ftp = self._connect()
        try:
            if not overwrite:
                try:
                    ftp.size(remote)
                    raise FileExistsError(path)
                except error_perm:
                    pass
            bio = io.BytesIO(data)
            ftp.storbinary(f"STOR {remote}", bio)
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        remote = self._remote_path(path)
        ftp = self._connect()
        try:
            try:
                ftp.delete(remote)
                return
            except error_perm as exc:
                # Maybe a directory.
                if str(exc).startswith("550"):
                    try:
                        ftp.rmd(remote)
                        return
                    except error_perm as exc2:
                        if missing_ok and str(exc2).startswith("550"):
                            return
                        if str(exc2).startswith("550"):
                            raise FileNotFoundError(path) from exc2
                        raise
                raise
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def stat(self, path: str) -> StorageStat | None:
        remote = self._remote_path(path)
        ftp = self._connect()
        try:
            try:
                size = ftp.size(remote)
                if size is not None:
                    return StorageStat(
                        path=_clean_posix(path), is_dir=False, size=int(size)
                    )
            except error_perm:
                pass
            # Directory detection is not standardized; attempt CWD into it.
            cur = ftp.pwd()
            try:
                ftp.cwd(remote)
                ftp.cwd(cur)
                return StorageStat(path=_clean_posix(path), is_dir=True, size=None)
            except error_perm:
                return None
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        root = _clean_posix(path)
        ftp = self._connect()
        try:
            entries: list[StorageEntry] = []

            def _list_one(dir_path: str) -> list[tuple[str, bool]]:
                # Use MLSD when available; fallback to NLST.
                remote = self._remote_path(dir_path)
                items: list[tuple[str, bool]] = []
                try:
                    for name, facts in ftp.mlsd(remote):
                        if name in {".", ".."}:
                            continue
                        is_dir = facts.get("type") == "dir"
                        items.append((name, is_dir))
                    return items
                except Exception:
                    names = ftp.nlst(remote)
                    for full in names:
                        name = posixpath.basename(full.rstrip("/"))
                        if not name or name in {".", ".."}:
                            continue
                        # Best-effort is_dir: attempt cwd.
                        is_dir = False
                        cur = ftp.pwd()
                        try:
                            ftp.cwd(posixpath.join(remote, name))
                            ftp.cwd(cur)
                            is_dir = True
                        except Exception:
                            is_dir = False
                        items.append((name, is_dir))
                    return items

            queue: list[tuple[str, int]] = [(root, 0)]
            while queue:
                current, depth = queue.pop(0)
                for name, is_dir in _list_one(current):
                    child = _clean_posix(posixpath.join(current, name))
                    entries.append(StorageEntry(path=child, is_dir=is_dir))
                    if recursive and is_dir:
                        queue.append((child, depth + 1))
            return entries
        except error_perm as exc:
            if str(exc).startswith("550"):
                raise FileNotFoundError(path) from exc
            raise
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def create_dir(
        self, path: str, *, parents: bool = True, exist_ok: bool = True
    ) -> None:
        target = _clean_posix(path)
        parts = [p for p in target.split("/") if p]
        ftp = self._connect()
        try:
            current = "/"
            for part in parts:
                current = _clean_posix(posixpath.join(current, part))
                remote = self._remote_path(current)
                try:
                    ftp.mkd(remote)
                except error_perm as exc:
                    if exist_ok and str(exc).startswith("550"):
                        continue
                    raise
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        ftp = self._connect()
        try:
            rsrc = self._remote_path(src)
            rdst = self._remote_path(dst)
            if not overwrite:
                try:
                    ftp.size(rdst)
                    raise FileExistsError(dst)
                except error_perm:
                    pass
            ftp.rename(rsrc, rdst)
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        # FTP has no universal server-side copy; do client-side copy.
        data = self.read_bytes(src)
        self.write_bytes(dst, data, overwrite=overwrite)

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        raise NotSupportedError("chmod_path", backend=self.backend_name)
