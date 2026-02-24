"""Tests for Google Drive OAuth helper script.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Covers auth URL generation and token exchange helper behavior.
Requirements: FR1.32
Tasks: T23
Architecture: 9.2 Google Drive Backend
Tests: UT1.30
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.google_drive_oauth_helper import build_auth_url


def test_build_auth_url_contains_required_params() -> None:
    url = build_auth_url(
        client_id="client-id",
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        scopes=["https://www.googleapis.com/auth/drive"],
        state="abc123",
    )
    assert "accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=client-id" in url
    assert "response_type=code" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=abc123" in url


def test_helper_cli_prints_auth_url_without_code() -> None:
    script = Path("scripts/google_drive_oauth_helper.py")
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--client-id",
            "client-id",
            "--redirect-uri",
            "urn:ietf:wg:oauth:2.0:oob",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Authorization URL:" in proc.stdout
    assert "rerun with --code" in proc.stdout


def test_google_oauth_live_exchange_if_enabled() -> None:
    if os.getenv("FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST", "0") != "1":
        pytest.skip("Set FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST=1 to run live OAuth code exchange")
    client_id = os.getenv("FILE_MCP_GDRIVE_CLIENT_ID", "").strip()
    client_secret = os.getenv("FILE_MCP_GDRIVE_CLIENT_SECRET", "").strip()
    code = os.getenv("FILE_MCP_GDRIVE_AUTH_CODE", "").strip()
    if not client_id or not client_secret or not code:
        pytest.skip("Missing FILE_MCP_GDRIVE_CLIENT_ID/FILE_MCP_GDRIVE_CLIENT_SECRET/FILE_MCP_GDRIVE_AUTH_CODE")

    script = Path("scripts/google_drive_oauth_helper.py")
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--client-id",
            client_id,
            "--client-secret",
            client_secret,
            "--code",
            code,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Token exchange response received." in proc.stdout
    assert "FILE_MCP_GDRIVE_ACCESS_TOKEN=" in proc.stdout
