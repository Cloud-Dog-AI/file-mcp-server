"""Storage backend interfaces and common types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


class NotSupportedError(RuntimeError):
    """Raised when a capability is not supported by a storage backend."""

    def __init__(self, operation: str, *, backend: str) -> None:
        super().__init__(f"Not supported for backend: {operation} (backend={backend})")
        self.operation = operation
        self.backend = backend


@dataclass(frozen=True)
class StorageStat:
    path: str
    is_dir: bool
    size: int | None = None


@dataclass(frozen=True)
class StorageEntry:
    path: str
    is_dir: bool


class StorageBackend:
    """
    A minimal file-like API over a backing store.

    Paths are POSIX-style absolute paths (e.g. `/docs/readme.md`) within the
    backend's configured root/prefix. Scope enforcement happens separately.
    """

    backend_name: str = "unknown"

    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        raise NotImplementedError

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        raise NotImplementedError

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        raise NotImplementedError

    def stat(self, path: str) -> Optional[StorageStat]:
        raise NotImplementedError

    def create_dir(
        self, path: str, *, parents: bool = True, exist_ok: bool = True
    ) -> None:
        raise NotSupportedError("create_dir", backend=self.backend_name)

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        raise NotSupportedError("copy_path", backend=self.backend_name)

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        raise NotSupportedError("move_path", backend=self.backend_name)

    def rename_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        self.move_path(src, dst, overwrite=overwrite)

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        raise NotSupportedError("chmod_path", backend=self.backend_name)

    def iter_paths(
        self, roots: Iterable[str], *, max_depth: int | None = None
    ) -> Iterable[str]:
        """
        Enumerate file paths under the given roots (POSIX absolute paths).

        Used for search operations. Backends may choose efficient listing APIs.
        """

        for root in roots:
            for entry in self.list_dir(root, recursive=True):
                if not entry.is_dir:
                    yield entry.path
