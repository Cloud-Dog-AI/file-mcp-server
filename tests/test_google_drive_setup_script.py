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

from pathlib import Path

from scripts.google_drive_setup import extract_folder_id, write_env_values


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
