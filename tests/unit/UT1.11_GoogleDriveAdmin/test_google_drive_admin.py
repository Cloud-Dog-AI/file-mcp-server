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

"""Tests for server-hosted Google Drive admin flow helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Unit tests for admin OAuth state, config updates, and callback handling.
Requirements: FR1.32
Tasks: T23
Architecture: 8.3 Endpoint Health Lifecycle, 9.2 Google Drive Backend
Tests: UT1.32
"""

from __future__ import annotations

from pathlib import Path
import requests

from file_mcp_server import google_drive_admin as admin


def test_render_setup_page_contains_form_and_profiles() -> None:
    html = admin.render_setup_page(
        callback_url="http://example.test/admin/google-drive/callback",
        profiles=["default", "profile2"],
        selected_profile="profile2",
        status_message="ready",
        status_type="ok",
    )
    assert "Google Drive Profile Setup" in html
    assert "profile2" in html
    assert "/admin/google-drive/start" in html
    assert "selected" in html


def test_render_setup_page_locks_profile_when_requested() -> None:
    html = admin.render_setup_page(
        callback_url="http://example.test/admin/google-drive/callback",
        profiles=["default", "google_drive"],
        selected_profile="google_drive",
        lock_profile=True,
    )
    assert "Profile is fixed for this authorisation flow." in html
    assert "name='profile'" in html
    assert "disabled" in html


def test_render_setup_page_prefills_values_and_masks_stored_secret() -> None:
    html = admin.render_setup_page(
        callback_url="http://example.test/admin/google-drive/callback",
        profiles=["default"],
        prefills={
            "user_email": "gary@example.com",
            "folder_input": "https://drive.google.com/drive/folders/folder123",
            "client_id": "client-123",
            "client_secret": "raw-secret-should-not-render",
            "redirect_uri": "http://example.test/admin/google-drive/callback",
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        has_client_secret=True,
    )
    assert 'value="gary@example.com"' in html
    assert 'value="client-123"' in html
    assert "folder123" in html
    assert f'value="{admin.MASKED_CLIENT_SECRET}"' in html
    assert "raw-secret-should-not-render" not in html


def test_update_profile_google_drive_writes_selected_profile(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "profiles:\n  default:\n    storage:\n      backend: local\n  profile2:\n    storage:\n      backend: local\n",
        encoding="utf-8",
    )
    admin._update_profile_google_drive(
        config_path=cfg,
        profile="profile2",
        user_email="u@example.com",
        folder_id="folder123",
        folder_url="https://drive.google.com/drive/folders/folder123",
        client_id="cid",
        client_secret="csec",
        refresh_token="rtok",
        access_token="atok",
        redirect_uri="http://localhost",
        token_uri="https://oauth2.googleapis.com/token",
    )
    content = cfg.read_text(encoding="utf-8")
    assert "profile2" in content
    assert "backend: google_drive" in content
    assert "folder123" in content
    assert "client_id: cid" in content


def test_complete_oauth_callback_updates_config_with_monkeypatched_network(
    tmp_path: Path, monkeypatch
) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "profiles:\n  default:\n    storage:\n      backend: local\n", encoding="utf-8"
    )
    state = "state123"
    with admin._PENDING_LOCK:
        admin._PENDING[state] = admin.PendingGoogleDriveAuth(
            created_at=0.0,
            profile="default",
            user_email="u@example.com",
            folder_input="test",
            client_id="cid",
            client_secret="secret",
            oauth_scope="scope",
            oauth_authorize_uri="https://accounts.google.test/auth",
            api_base_uri="https://drive.googleapis.test/v3",
            redirect_uri="http://localhost",
            token_uri="https://oauth2.googleapis.com/token",
        )
    monkeypatch.setattr(admin, "_exchange_code", lambda pending, code: ("atok", "rtok"))
    monkeypatch.setattr(
        admin,
        "_fetch_folder",
        lambda access_token, folder_input, api_base_uri: (
            "folder1",
            "test",
            "https://drive.google.com/drive/folders/folder1",
        ),
    )
    result = admin.complete_oauth_callback(state=state, code="code123", config_path=cfg)
    assert result.profile == "default"
    assert result.folder_id == "folder1"
    updated = cfg.read_text(encoding="utf-8")
    assert "backend: google_drive" in updated


def test_fetch_folder_falls_back_to_name_lookup_on_404(monkeypatch) -> None:
    class _Resp:
        def __init__(self, status_code: int, data: dict) -> None:
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"status={self.status_code}")

    calls = {"n": 0}

    def _fake_get(url, headers=None, params=None, timeout=None):  # noqa: ANN001
        calls["n"] += 1
        if "/drive/v3/files/Test" in url:
            return _Resp(404, {})
        return _Resp(
            200,
            {
                "files": [
                    {
                        "id": "folder123",
                        "name": "Test",
                        "webViewLink": "https://drive.google.com/drive/folders/folder123",
                        "mimeType": "application/vnd.google-apps.folder",
                    }
                ]
            },
        )

    monkeypatch.setattr(admin, "http_get", _fake_get)
    folder_id, folder_name, folder_url = admin._fetch_folder(
        "atok", "Test", api_base_uri="https://www.googleapis.com/drive/v3"
    )
    assert folder_id == "folder123"
    assert folder_name == "Test"
    assert "folder123" in folder_url
    assert calls["n"] == 2
