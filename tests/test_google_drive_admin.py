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

from file_mcp_server import google_drive_admin as admin


def test_render_setup_page_contains_form_and_profiles() -> None:
    html = admin.render_setup_page(
        callback_url="http://example.test/admin/google-drive/callback",
        profiles=["default", "profile2"],
        status_message="ready",
        status_type="ok",
    )
    assert "Google Drive Profile Setup" in html
    assert "profile2" in html
    assert "/admin/google-drive/start" in html


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


def test_complete_oauth_callback_updates_config_with_monkeypatched_network(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("profiles:\n  default:\n    storage:\n      backend: local\n", encoding="utf-8")
    state = "state123"
    with admin._PENDING_LOCK:
        admin._PENDING[state] = admin.PendingGoogleDriveAuth(
            created_at=0.0,
            profile="default",
            user_email="u@example.com",
            folder_input="test",
            client_id="cid",
            client_secret="secret",
            redirect_uri="http://localhost",
            token_uri="https://oauth2.googleapis.com/token",
        )
    monkeypatch.setattr(admin, "_exchange_code", lambda pending, code: ("atok", "rtok"))
    monkeypatch.setattr(
        admin,
        "_fetch_folder",
        lambda access_token, folder_input: ("folder1", "test", "https://drive.google.com/drive/folders/folder1"),
    )
    result = admin.complete_oauth_callback(state=state, code="code123", config_path=cfg)
    assert result.profile == "default"
    assert result.folder_id == "folder1"
    updated = cfg.read_text(encoding="utf-8")
    assert "backend: google_drive" in updated
