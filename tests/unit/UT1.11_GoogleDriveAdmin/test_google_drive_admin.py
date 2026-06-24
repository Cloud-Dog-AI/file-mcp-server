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
import pytest

from pathlib import Path
import requests

from file_mcp_server import google_drive_admin as admin
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


def test_merge_google_drive_into_profile_builds_db_profile_payload() -> None:
    profile = {"storage": {"backend": "local"}}
    admin._merge_google_drive_into_profile(
        profile,
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
    storage = profile["storage"]
    assert storage["backend"] == "google_drive"
    drive = storage["google_drive"]
    assert drive["folder_id"] == "folder123"
    assert drive["client_id"] == "cid"
    assert drive["refresh_token"] == "rtok"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


def test_complete_oauth_callback_persists_to_db_and_does_not_mutate_config_yaml(
    tmp_path: Path, monkeypatch
) -> None:
    """W28M-1605-FIX: the callback (1) REFUSES without a durable DB store, and
    (2) with the DB writes Google Drive profile material ONLY to the
    file_storage_profiles row. Runtime config.yaml remains immutable."""
    import json as _json

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "profiles:\n  default:\n    storage:\n      backend: local\n", encoding="utf-8"
    )
    original_config = cfg.read_text(encoding="utf-8")
    # distinctive secret values so a substring leak is unambiguous
    A_TOK, R_TOK, C_SECRET = "ATOK_w28m1605_uniq", "RTOK_w28m1605_uniq", "CSECRET_w28m1605_uniq"
    monkeypatch.setattr(admin, "_exchange_code", lambda pending, code: (A_TOK, R_TOK))
    monkeypatch.setattr(
        admin,
        "_fetch_folder",
        lambda access_token, folder_input, api_base_uri: (
            "folder1",
            "test",
            "https://drive.google.com/drive/folders/folder1",
        ),
    )

    def _seed_pending(state: str) -> None:
        with admin._PENDING_LOCK:
            admin._PENDING[state] = admin.PendingGoogleDriveAuth(
                created_at=0.0,
                profile="default",
                user_email="u@example.com",
                folder_input="test",
                client_id="cid",
                client_secret=C_SECRET,
                oauth_scope="scope",
                oauth_authorize_uri="https://accounts.google.test/auth",
                api_base_uri="https://drive.googleapis.test/v3",
                redirect_uri="http://localhost",
                token_uri="https://oauth2.googleapis.com/token",
            )

    # 1) refuses to complete without a durable DB store (fails fast)
    _seed_pending("state-nodb")
    with pytest.raises(RuntimeError, match="durable database"):
        admin.complete_oauth_callback(state="state-nodb", code="c", config_path=cfg)

    # 2) with the DB: config.yaml is unchanged; DB gets the full profile material.
    monkeypatch.setenv("FILE_MCP_DB_URL", f"sqlite:///{tmp_path}/db/file_mcp.db")
    from file_mcp_server.db.runtime import initialise_database
    from file_mcp_server.db.models import FileStorageProfile

    rt = initialise_database(force_reinit=True)
    _seed_pending("state-db")
    result = admin.complete_oauth_callback(
        state="state-db",
        code="code123",
        config_path=cfg,
        db_session_manager=rt.session_manager,
        file_storage_profile_model=FileStorageProfile,
    )
    assert result.profile == "default"
    assert result.folder_id == "folder1"

    updated = cfg.read_text(encoding="utf-8")
    assert updated == original_config
    for secret in (A_TOK, R_TOK, C_SECRET):
        assert secret not in updated

    with rt.session_manager.session() as session:
        row = (
            session.query(FileStorageProfile)
            .filter_by(name="default", is_active=True)
            .first()
        )
        drive = _json.loads(row.config_json)["storage"]["google_drive"]
    assert drive["refresh_token"] == R_TOK
    assert drive["access_token"] == A_TOK
    assert drive["client_secret"] == C_SECRET
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")


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


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-015")
def test_render_link_success_page_is_styled_linked_and_leak_free() -> None:
    """W28M-1605-FIX: the Google Drive link-success page is a full, styled HTML
    document with continue links and NO internal leaks (config.yaml path / DB row id)."""
    result = admin.GoogleDriveBindResult(
        profile="google_drive",
        user_email="demo@cloud-dog.net",
        folder_id="FID-123",
        folder_name="tests",
        folder_url="https://drive.google.com/drive/folders/FID-123",
        config_path="/app/config.yaml",
        db_row_id="prof_225287ce97c9",
    )
    html = admin.render_link_success_page(result, continue_url="/admin/google-drive")
    # styled, rendered full document
    assert html.lstrip().startswith("<!doctype html>")
    assert "<style>" in html and "</style>" in html
    assert "<title>" in html
    # continue link present
    assert 'href="/admin/google-drive"' in html
    assert "Continue" in html
    # surfaces the linked folder + folder link
    assert "tests" in html
    assert "https://drive.google.com/drive/folders/FID-123" in html
    # NEVER leaks internal detail
    assert "/app/config.yaml" not in html
    assert "prof_225287ce97c9" not in html
    assert "DB row" not in html
    # not-persisted variant warns (still no leaks)
    result.db_row_id = None
    warn_html = admin.render_link_success_page(result, persisted=False)
    assert "not saved durably" in warn_html.lower()
    assert "/app/config.yaml" not in warn_html
