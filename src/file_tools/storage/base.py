# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# """
# License: Apache 2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
file-mcp-server — file_tools/storage/base.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for storage base.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Optional


class NotSupportedError(RuntimeError):
    """Raised when a capability is not supported by a storage backend."""

    def __init__(self, operation: str, *, backend: str) -> None:
        """Initialise the instance state."""
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


class StorageBackend(ABC):
    """
    A minimal file-like API over a backing store.

    Paths are POSIX-style absolute paths (e.g. `/docs/readme.md`) within the
    backend's configured root/prefix. Scope enforcement happens separately.
    """

    backend_name: str = "unknown"

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read bytes."""
        raise NotSupportedError("read_bytes", backend=self.backend_name)

    @abstractmethod
    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        """Write bytes."""
        raise NotSupportedError("write_bytes", backend=self.backend_name)

    @abstractmethod
    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        """Delete path."""
        raise NotSupportedError("delete_path", backend=self.backend_name)

    @abstractmethod
    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        """List dir."""
        raise NotSupportedError("list_dir", backend=self.backend_name)

    @abstractmethod
    def stat(self, path: str) -> Optional[StorageStat]:
        """Execute stat."""
        raise NotSupportedError("stat", backend=self.backend_name)

    def create_dir(
        self, path: str, *, parents: bool = True, exist_ok: bool = True
    ) -> None:
        """Create dir."""
        raise NotSupportedError("create_dir", backend=self.backend_name)

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Copy path."""
        raise NotSupportedError("copy_path", backend=self.backend_name)

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Move path."""
        raise NotSupportedError("move_path", backend=self.backend_name)

    def rename_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Rename path."""
        self.move_path(src, dst, overwrite=overwrite)

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        """Execute chmod path."""
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


def is_unresolved_placeholder(value: object) -> bool:
    """Return True when a value still contains an unresolved ${...} placeholder."""
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    return cleaned.startswith("${") and cleaned.endswith("}")
