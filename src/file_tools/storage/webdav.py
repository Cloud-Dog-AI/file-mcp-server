"""WebDAV storage backend."""

from __future__ import annotations

import posixpath
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urljoin, urlparse

import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree as ET

from file_tools.config.models import StorageConfig

from .base import NotSupportedError, StorageBackend, StorageEntry, StorageStat

_DEFAULT_MOVE_RETRY_STATUSES = {408, 409, 423, 425, 429, 500, 502, 503, 504}


def _clean_posix(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    norm = posixpath.normpath(path)
    if not norm.startswith("/"):
        norm = "/" + norm
    return norm


def _join_url(base_url: str, rel_path: str) -> str:
    # WebDAV base_url is treated as the root directory. Map `/` to base_url and
    # `/a/b.txt` to `${base_url}/a/b.txt`, quoting each segment.
    base = base_url.rstrip("/") + "/"
    rel = _clean_posix(rel_path).lstrip("/")
    if not rel:
        return base.rstrip("/")
    parts = [quote(seg) for seg in rel.split("/")]
    return urljoin(base, "/".join(parts))


def _dav_ns(tag: str) -> str:
    return f"{{DAV:}}{tag}"


def _to_int(value: object, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or "${" in cleaned:
            return default
        try:
            return int(cleaned)
        except ValueError:
            return default
    return default


def _to_float(value: object, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or "${" in cleaned:
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def _parse_retry_statuses(value: object) -> set[int]:
    if not isinstance(value, str):
        return set(_DEFAULT_MOVE_RETRY_STATUSES)
    cleaned = value.strip()
    if not cleaned or "${" in cleaned:
        return set(_DEFAULT_MOVE_RETRY_STATUSES)
    out: set[int] = set()
    for part in cleaned.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            code = int(token)
        except ValueError:
            continue
        if 100 <= code <= 599:
            out.add(code)
    return out or set(_DEFAULT_MOVE_RETRY_STATUSES)


@dataclass(frozen=True)
class _DavItem:
    path: str
    is_dir: bool
    size: int | None = None


def _parse_propfind_xml(body: bytes, *, base_url: str) -> list[_DavItem]:
    out: list[_DavItem] = []
    root = ET.fromstring(body)
    for resp in root.findall(_dav_ns("response")):
        href_el = resp.find(_dav_ns("href"))
        if href_el is None or not href_el.text:
            continue
        href = href_el.text
        # Map href URL path back to logical path relative to base_url path.
        base_path = urlparse(base_url).path.rstrip("/")
        href_path = urlparse(href).path
        if base_path and href_path.startswith(base_path):
            rel = href_path[len(base_path) :]
        else:
            rel = href_path
        logical = _clean_posix(rel)

        propstat = resp.find(_dav_ns("propstat"))
        prop = propstat.find(_dav_ns("prop")) if propstat is not None else None
        is_dir = False
        size: int | None = None
        if prop is not None:
            rtype = prop.find(_dav_ns("resourcetype"))
            if rtype is not None and rtype.find(_dav_ns("collection")) is not None:
                is_dir = True
            clen = prop.find(_dav_ns("getcontentlength"))
            if clen is not None and clen.text:
                try:
                    size = int(clen.text.strip())
                except ValueError:
                    size = None
        out.append(_DavItem(path=logical, is_dir=is_dir, size=size))
    return out


class WebDavStorage(StorageBackend):
    backend_name = "webdav"

    def __init__(self, storage: StorageConfig, *, timeout_s: int | None = None) -> None:
        if not storage.webdav.base_url:
            raise ValueError("WebDAV storage requires webdav.base_url")
        self._base_url = storage.webdav.base_url.rstrip("/")
        self._auth = HTTPBasicAuth(storage.webdav.username or "", storage.webdav.password or "")
        self._verify: bool | str = True
        insecure = (storage.tls.insecure_skip_verify or "").strip().lower()
        if insecure in {"1", "true", "yes", "on"}:
            self._verify = False
        elif storage.tls.ca_bundle_path:
            self._verify = storage.tls.ca_bundle_path

        self._timeout_s: float | None = float(timeout_s) if timeout_s is not None else None
        self._move_retry_count = _to_int(storage.webdav.move_retry_count, default=2)
        self._move_retry_backoff_s = _to_float(storage.webdav.move_retry_backoff_s, default=0.35)
        self._move_probe_timeout_s = _to_float(
            storage.webdav.move_probe_timeout_s,
            default=min(5.0, self._timeout_s or 5.0),
        )
        self._move_retry_statuses = _parse_retry_statuses(storage.webdav.move_retry_statuses)

    def _is_transient_status(self, status_code: int) -> bool:
        return status_code in self._move_retry_statuses

    def _path_exists(self, path: str) -> bool:
        try:
            url = _join_url(self._base_url, path)
            resp = self._request("PROPFIND", url, headers={"Depth": "0"}, timeout_s=self._move_probe_timeout_s)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            return True
        except Exception:
            return False

    def _move_already_applied(self, src: str, dst: str) -> bool:
        # Some WebDAV servers can return a transient 5xx during MOVE even when
        # destination was already committed. Treat "src missing + dst present" as success.
        src_exists = self._path_exists(src)
        dst_exists = self._path_exists(dst)
        return (not src_exists) and dst_exists

    def _request(self, method: str, url: str, *, headers: dict[str, str] | None = None, data: bytes | None = None,
                 timeout_s: float | None = None, stream: bool = False) -> requests.Response:
        return requests.request(
            method,
            url,
            headers=headers,
            data=data,
            auth=self._auth,
            verify=self._verify,
            timeout=(timeout_s if timeout_s is not None else self._timeout_s),
            stream=stream,
        )

    def read_bytes(self, path: str) -> bytes:
        url = _join_url(self._base_url, path)
        resp = self._request("GET", url)
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        resp.raise_for_status()
        return resp.content

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        if not overwrite:
            # WebDAV has If-None-Match: * semantics for "create only".
            headers = {"If-None-Match": "*"}
        else:
            headers = {}
        url = _join_url(self._base_url, path)
        resp = self._request("PUT", url, headers=headers, data=data)
        if resp.status_code in (200, 201, 204):
            return
        if resp.status_code == 412 and not overwrite:
            raise FileExistsError(path)
        resp.raise_for_status()

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        url = _join_url(self._base_url, path)
        resp = self._request("DELETE", url)
        if resp.status_code == 404 and missing_ok:
            return
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        resp.raise_for_status()

    def stat(self, path: str) -> StorageStat | None:
        url = _join_url(self._base_url, path)
        headers = {"Depth": "0"}
        resp = self._request("PROPFIND", url, headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        items = _parse_propfind_xml(resp.content, base_url=self._base_url)
        if not items:
            return None
        item = items[0]
        return StorageStat(path=item.path, is_dir=item.is_dir, size=item.size)

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        # Default to Depth:1 for non-recursive, Depth:infinity for recursive.
        url = _join_url(self._base_url, path)
        headers = {"Depth": "infinity" if recursive else "1"}
        resp = self._request("PROPFIND", url, headers=headers)
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        resp.raise_for_status()
        items = _parse_propfind_xml(resp.content, base_url=self._base_url)
        # The first item is the directory itself; drop it.
        cleaned: list[StorageEntry] = []
        base = _clean_posix(path)
        for item in items:
            if _clean_posix(item.path) == base:
                continue
            cleaned.append(StorageEntry(path=item.path, is_dir=item.is_dir))
        return cleaned

    def create_dir(self, path: str, *, parents: bool = True, exist_ok: bool = True) -> None:
        # WebDAV MKCOL does not create parents; create chain if requested.
        target = _clean_posix(path)
        parts = [p for p in target.split("/") if p]
        current = "/"
        for part in parts:
            current = _clean_posix(posixpath.join(current, part))
            url = _join_url(self._base_url, current)
            resp = self._request("MKCOL", url)
            if resp.status_code in (200, 201, 204):
                continue
            if resp.status_code in (405, 409):
                # 405 Method Not Allowed is commonly returned if collection exists.
                # 409 Conflict can happen if parent missing when not using parents.
                if resp.status_code == 409 and not parents:
                    resp.raise_for_status()
                if exist_ok or resp.status_code == 405:
                    continue
            resp.raise_for_status()

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        src_url = _join_url(self._base_url, src)
        dst_url = _join_url(self._base_url, dst)
        headers = {"Destination": dst_url, "Overwrite": "T" if overwrite else "F"}
        resp = self._request("COPY", src_url, headers=headers)
        if resp.status_code == 412 and not overwrite:
            raise FileExistsError(dst)
        resp.raise_for_status()

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        src_url = _join_url(self._base_url, src)
        dst_url = _join_url(self._base_url, dst)
        headers = {"Destination": dst_url, "Overwrite": "T" if overwrite else "F"}
        attempts = self._move_retry_count + 1
        for attempt in range(1, attempts + 1):
            try:
                resp = self._request("MOVE", src_url, headers=headers)
                if resp.status_code in (200, 201, 204):
                    return
                if resp.status_code == 412 and not overwrite:
                    raise FileExistsError(dst)
                if self._is_transient_status(resp.status_code):
                    if self._move_already_applied(src, dst):
                        return
                    if attempt < attempts:
                        time.sleep(self._move_retry_backoff_s * attempt)
                        continue
                resp.raise_for_status()
                return
            except requests.RequestException:
                if self._move_already_applied(src, dst):
                    return
                if attempt < attempts:
                    time.sleep(self._move_retry_backoff_s * attempt)
                    continue
                raise

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        raise NotSupportedError("chmod_path", backend=self.backend_name)
