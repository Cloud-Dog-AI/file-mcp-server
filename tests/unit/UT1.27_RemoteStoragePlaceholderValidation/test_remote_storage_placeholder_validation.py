from __future__ import annotations

import pytest

from file_tools.config.models import StorageConfig
from file_tools.storage.ftp import FtpStorage
from file_tools.storage.google_drive import GoogleDriveStorage
from file_tools.storage.s3 import S3Storage
from file_tools.storage.webdav import WebDavStorage


def test_s3_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "s3",
            "s3": {
                "endpoint": "https://storage.cloud-dog.net",
                "bucket": "test",
                "access_key": "${vault.dev.storage.s3.access_key_id}",
                "secret_key": "${vault.dev.storage.s3.secret_access_key}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        S3Storage(cfg)


def test_webdav_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "webdav",
            "webdav": {
                "base_url": "https://files.cloud-dog.net/remote.php/dav/files/gary/temp",
                "username": "${vault.dev.storage.webdav.username}",
                "password": "${vault.dev.storage.webdav.password}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        WebDavStorage(cfg)


def test_ftp_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "ftp",
            "ftp": {
                "host": "ftp.cloud-dog.net",
                "username": "${vault.dev.storage.ftp.username}",
                "password": "${vault.dev.storage.ftp.password}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        FtpStorage(cfg)


def test_google_drive_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "google_drive",
            "google_drive": {
                "folder_id": "folder-id",
                "client_id": "${vault.dev.storage.google_drive.client_id}",
                "client_secret": "${vault.dev.storage.google_drive.client_secret}",
                "refresh_token": "${vault.dev.storage.google_drive.refresh_token}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        GoogleDriveStorage(cfg)
