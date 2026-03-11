"""Application test for live Google OAuth token exchange.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Validates live OAuth code exchange path for Google Drive helper.
Requirements: FR1.32
Tasks: W28A-90-R2
Architecture: 9.2 Google Drive Backend
Tests: AT1.12
"""

from __future__ import annotations

from tests.env_runtime import env_get

from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    os.environ.get("FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST") != "1",
    reason="GDrive deferred: requires web OAuth interface (W28A-121)",
)
def test_google_oauth_live_exchange_if_enabled() -> None:
    if env_get("FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST=1 to run live OAuth code exchange"
        )
    client_id = env_get("FILE_MCP_GDRIVE_CLIENT_ID", "").strip()
    client_secret = env_get("FILE_MCP_GDRIVE_CLIENT_SECRET", "").strip()
    code = env_get("FILE_MCP_GDRIVE_AUTH_CODE", "").strip()
    if not client_id or not client_secret or not code:
        pytest.fail(
            "Missing FILE_MCP_GDRIVE_CLIENT_ID/FILE_MCP_GDRIVE_CLIENT_SECRET/FILE_MCP_GDRIVE_AUTH_CODE"
        )

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
