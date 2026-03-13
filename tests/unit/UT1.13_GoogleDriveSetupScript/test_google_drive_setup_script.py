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

"""Unit tests for interactive Google Drive setup script helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Validates folder-id parsing and env-file update behavior.
Requirements: FR1.32
Tasks: T23
Architecture: 9.2 Google Drive Backend
Tests: UT1.31
"""

from __future__ import annotations

import json
from pathlib import Path

import urllib.request

import pytest

from scripts.google_drive_setup import (
    _load_google_defaults_from_credentials_file,
    _load_google_defaults_from_vault_blob,
    extract_folder_id,
    write_env_values,
)


def test_extract_folder_id_from_share_url() -> None:
    folder_id, folder_url = extract_folder_id(
        "https://drive.google.com/drive/folders/1r6kwtGcunVpkbT3nBGmfcWyVfk84_Sjn?usp=drive_link"
    )
    assert folder_id == "1r6kwtGcunVpkbT3nBGmfcWyVfk84_Sjn"
    assert folder_url and folder_url.startswith("https://drive.google.com/")


def test_extract_folder_id_from_literal_id() -> None:
    folder_id, folder_url = extract_folder_id("abc123-folder-id")
    assert folder_id == "abc123-folder-id"
    assert folder_url is None


def test_write_env_values_updates_existing_and_appends_new(tmp_path: Path) -> None:
    env_path = tmp_path / "env"
    env_path.write_text(
        "\n".join(
            [
                "# existing",
                "FILE_MCP_GDRIVE_CLIENT_ID=old-id",
                "FILE_MCP_GDRIVE_CLIENT_SECRET=old-secret",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_env_values(
        env_path,
        {
            "FILE_MCP_GDRIVE_CLIENT_ID": "new-id",
            "FILE_MCP_GDRIVE_REFRESH_TOKEN": "refresh-token",
        },
    )
    content = env_path.read_text(encoding="utf-8")
    assert "FILE_MCP_GDRIVE_CLIENT_ID=new-id" in content
    assert "FILE_MCP_GDRIVE_CLIENT_SECRET=old-secret" in content
    assert "FILE_MCP_GDRIVE_REFRESH_TOKEN=refresh-token" in content


def test_load_google_defaults_from_credentials_file(tmp_path: Path) -> None:
    private_dir = tmp_path / "private"
    private_dir.mkdir(parents=True)
    creds_path = private_dir / "googledrivecredentials.json"
    creds_path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "cid-123",
                    "client_secret": "csec-123",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        "http://127.0.0.1:8000/admin/google-drive/callback",
                        "http://localhost:8000/admin/google-drive/callback",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    defaults = _load_google_defaults_from_credentials_file(tmp_path)

    assert defaults["FILE_MCP_GDRIVE_CLIENT_ID"] == "cid-123"
    assert defaults["FILE_MCP_GDRIVE_CLIENT_SECRET"] == "csec-123"
    assert (
        defaults["FILE_MCP_GDRIVE_TOKEN_URI"] == "https://oauth2.googleapis.com/token"
    )
    assert (
        defaults["FILE_MCP_GDRIVE_REDIRECT_URI"]
        == "http://127.0.0.1:8000/admin/google-drive/callback"
    )


def test_load_google_defaults_from_vault_blob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example")
    monkeypatch.setenv("VAULT_TOKEN", "token-value")
    monkeypatch.setenv("VAULT_MOUNT_POINT", "cloud_dog_ai")
    monkeypatch.setenv("VAULT_CONFIG_PATH", "config")

    payload = {
        "data": {
            "data": {
                "json": {
                    "dev": {
                        "storage": {
                            "google_drive": {
                                "client_id": "vault-client-id",
                                "client_secret": "vault-client-secret",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": [
                                    "http://127.0.0.1:8000/admin/google-drive/callback"
                                ],
                            }
                        }
                    }
                }
            }
        }
    }

    class _Response:
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    def _fake_urlopen(req, context=None, timeout=None):  # type: ignore[no-untyped-def]
        return _Response()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    defaults = _load_google_defaults_from_vault_blob(tmp_path)

    assert defaults["FILE_MCP_GDRIVE_CLIENT_ID"] == "vault-client-id"
    assert defaults["FILE_MCP_GDRIVE_CLIENT_SECRET"] == "vault-client-secret"
    assert (
        defaults["FILE_MCP_GDRIVE_TOKEN_URI"] == "https://oauth2.googleapis.com/token"
    )
    assert (
        defaults["FILE_MCP_GDRIVE_REDIRECT_URI"]
        == "http://127.0.0.1:8000/admin/google-drive/callback"
    )
