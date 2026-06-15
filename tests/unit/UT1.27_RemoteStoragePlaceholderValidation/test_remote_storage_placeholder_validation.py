# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
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

from __future__ import annotations

import pytest

from file_tools.config.models import StorageConfig
from file_tools.storage.ftp import FtpStorage
from file_tools.storage.google_drive import GoogleDriveStorage
from file_tools.storage.s3 import S3Storage
from file_tools.storage.webdav import WebDavStorage
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_s3_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "s3",
            "s3": {
                "endpoint": "https://storage.example.com",
                "bucket": "test",
                "access_key": "${vault.dev.storage.s3.access_key_id}",
                "secret_key": "${vault.dev.storage.s3.secret_access_key}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        S3Storage(cfg)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_webdav_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "webdav",
            "webdav": {
                "base_url": "https://files.example.com/remote.php/dav/files/user/temp",
                "username": "${vault.dev.storage.webdav.username}",
                "password": "${vault.dev.storage.webdav.password}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        WebDavStorage(cfg)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_ftp_rejects_unresolved_placeholder_credentials() -> None:
    cfg = StorageConfig.model_validate(
        {
            "backend": "ftp",
            "ftp": {
                "host": "ftp.example.com",
                "username": "${vault.dev.storage.ftp.username}",
                "password": "${vault.dev.storage.ftp.password}",
            },
        }
    )
    with pytest.raises(ValueError, match="placeholder found"):
        FtpStorage(cfg)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


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
