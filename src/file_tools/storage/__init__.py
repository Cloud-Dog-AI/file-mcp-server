"""Storage backends for file-mcp-server.

This module provides a minimal abstraction so the same tool surface can operate
on different storage systems (local filesystem, S3-compatible, WebDAV, FTP).
"""

from .base import NotSupportedError, StorageBackend, StorageEntry, StorageStat
from .factory import build_storage_backend

__all__ = [
    "NotSupportedError",
    "StorageBackend",
    "StorageEntry",
    "StorageStat",
    "build_storage_backend",
]
