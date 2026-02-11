"""Local filesystem storage backend (existing behavior)."""

from __future__ import annotations

from pathlib import Path

from file_tools.io.filesystem import (
    chmod_path as fs_chmod_path,
    copy_file,
    create_dir,
    delete_file,
    list_dir as fs_list_dir,
    move_path,
    read_bytes,
    write_bytes,
)

from .base import StorageBackend, StorageEntry, StorageStat


class LocalStorage(StorageBackend):
    backend_name = "local"

    def __init__(self) -> None:
        # Local storage uses OS filesystem; no extra configuration needed.
        pass

    def read_bytes(self, path: str) -> bytes:
        return read_bytes(Path(path))

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        write_bytes(Path(path), data, overwrite=overwrite)

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        delete_file(Path(path), missing_ok=missing_ok)

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        entries = fs_list_dir(Path(path), recursive=recursive)
        out: list[StorageEntry] = []
        for item in entries:
            try:
                is_dir = item.is_dir()
            except OSError:
                is_dir = False
            out.append(StorageEntry(path=str(item), is_dir=is_dir))
        return out

    def stat(self, path: str) -> StorageStat | None:
        p = Path(path)
        if not p.exists():
            return None
        return StorageStat(path=str(p), is_dir=p.is_dir(), size=(p.stat().st_size if p.is_file() else None))

    def create_dir(self, path: str, *, parents: bool = True, exist_ok: bool = True) -> None:
        create_dir(Path(path), parents=parents, exist_ok=exist_ok)

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        copy_file(Path(src), Path(dst), overwrite=overwrite)

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        move_path(Path(src), Path(dst), overwrite=overwrite)

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        fs_chmod_path(Path(path), mode, recursive=recursive)
