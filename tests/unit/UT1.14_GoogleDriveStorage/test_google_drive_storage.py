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

"""Google Drive storage unit tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Validate URL parsing and required config checks for Google Drive backend.
Requirements: FR2.5
Tasks: T23
Architecture: 4. Storage Backends
Tests: UT1.29
"""

from __future__ import annotations

import pytest

from file_tools.adapters import Response
from file_tools.config.models import StorageConfig
from file_tools.storage.google_drive import GoogleDriveStorage, _extract_folder_id
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-021")


def test_extract_folder_id_from_drive_url() -> None:
    folder_id = _extract_folder_id(
        None,
        "https://drive.google.com/drive/folders/1r6kwtGcunVpkbT3nBGmfcWyVfk84_Sjn?usp=drive_link",
    )
    assert folder_id == "1r6kwtGcunVpkbT3nBGmfcWyVfk84_Sjn"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-021")


def test_google_drive_requires_folder_id_or_url() -> None:
    storage = StorageConfig(
        backend="google_drive",
        google_drive={
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "token",
        },
    )
    with pytest.raises(ValueError, match="folder_id or google_drive.folder_url"):
        GoogleDriveStorage(storage)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-021")


def test_google_drive_requires_oauth_client() -> None:
    storage = StorageConfig(
        backend="google_drive",
        google_drive={
            "folder_id": "folder",
            "refresh_token": "token",
        },
    )
    with pytest.raises(ValueError, match="client_id and google_drive.client_secret"):
        GoogleDriveStorage(storage)


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-021")
def test_google_drive_defaults_upload_base_uri() -> None:
    storage = StorageConfig(
        backend="google_drive",
        google_drive={
            "folder_id": "folder",
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "api_base_uri": "https://www.googleapis.com/drive/v3",
        },
    )

    backend = GoogleDriveStorage(storage)

    assert backend._upload_base_uri == "https://www.googleapis.com/upload/drive/v3"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-021")
def test_google_drive_token_refresh_surfaces_invalid_grant(monkeypatch) -> None:
    storage = StorageConfig(
        backend="google_drive",
        google_drive={
            "folder_id": "folder",
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "api_base_uri": "https://www.googleapis.com/drive/v3",
            "upload_base_uri": "https://www.googleapis.com/upload/drive/v3",
        },
    )

    def fake_request(*_args, **_kwargs):
        response = Response()
        response.status_code = 400
        response.reason = "Bad Request"
        response.url = "https://oauth2.googleapis.com/token"
        response._content = (
            b'{"error":"invalid_grant",'
            b'"error_description":"Token has been expired or revoked."}'
        )
        return response

    monkeypatch.setattr("file_tools.storage.google_drive.http_request", fake_request)
    backend = GoogleDriveStorage(storage)

    with pytest.raises(RuntimeError, match="invalid_grant.*expired or revoked"):
        backend._token()
