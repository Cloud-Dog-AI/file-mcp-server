"""
file-mcp-server — file_tools/storage/factory.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for storage factory.py.
"""

from __future__ import annotations

from file_tools.config.models import ProfileConfig

from .base import StorageBackend
from .local import LocalStorage


def build_storage_backend(profile: ProfileConfig) -> StorageBackend:
    """Build storage backend."""
    backend = (profile.storage.backend or "local").strip().lower()
    timeout_s = profile.limits.storage_timeout_s
    if backend in {"", "local", "filesystem", "fs"}:
        return LocalStorage()
    # Backends are added in dedicated modules (s3/webdav/ftp). Import lazily to
    # avoid pulling optional deps at import time.
    if backend == "s3":
        from .s3 import S3Storage

        return S3Storage(profile.storage, timeout_s=timeout_s)
    if backend == "webdav":
        from .webdav import WebDavStorage

        return WebDavStorage(profile.storage, timeout_s=timeout_s)
    if backend == "ftp":
        from .ftp import FtpStorage

        return FtpStorage(profile.storage, timeout_s=timeout_s)
    if backend in {"google_drive", "gdrive", "drive"}:
        from .google_drive import GoogleDriveStorage

        return GoogleDriveStorage(profile.storage, timeout_s=timeout_s)
    raise ValueError(f"Unknown storage backend: {backend}")
