"""System tests for endpoint health restart threshold behavior.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Verifies server exit behavior when endpoint restart threshold is reached.
Requirements: FR1.30, FR1.31
Tasks: T22
Architecture: 8.3 Endpoint Health Lifecycle
Tests: ST1.8
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def test_server_exits_when_restart_threshold_reached(tmp_path: Path) -> None:
    repo_root = Path.cwd()
    defaults_path = repo_root / "defaults.yaml"
    config_path = tmp_path / "config.restart-threshold.yaml"
    env_path = tmp_path / "env.restart-threshold"
    pidfile = tmp_path / "restart.pid"

    config_path.write_text(
        dedent(
            """
            profiles:
              default:
                endpoint_health:
                  enabled: true
                  check_on_startup: true
                  check_all_configured_backends: false
                  max_retries: 0
                  retry_interval_s: 1
                  retry_window_s: 60
                  max_failures_before_restart: 1
                  recover_after_s: 30
                  restart_on_threshold: true
                  restart_exit_code: 76
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    env_path.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_PRIMARY=secret",
                "FILE_MCP_AUTH_HEADER_NAME=Authorization",
                "FILE_MCP_AUTH_HEADER_SCHEME=Bearer",
                "FILE_MCP_ROOT=/",
                "FILE_MCP_AUDIT_LOG=./working/restart-threshold/audit.log.jsonl",
                "FILE_MCP_SERVER_LOG=./working/restart-threshold/server.log",
                "FILE_MCP_SNAPSHOT_DIR=./working/restart-threshold/snapshots",
                "FILE_MCP_HTTP_TRANSPORT=streamable-http",
                "FILE_MCP_HTTP_HOST=127.0.0.1",
                "FILE_MCP_HTTP_PORT=48231",
                "FILE_MCP_HTTP_BASE_PATH=/",
                "FILE_MCP_HTTP_MCP_PATH=/mcp",
                "FILE_MCP_HTTP_HEALTH_PATH=/health",
                "FILE_MCP_HTTP_EVENTS_PATH=/events",
                "FILE_MCP_HTTP_STATELESS=true",
                "FILE_MCP_SEARCH_MAX_RESULTS=50",
                "FILE_MCP_SEARCH_MAX_FILE_MB=5",
                "FILE_MCP_SEARCH_TIMEOUT_S=10",
                "FILE_MCP_STORAGE_TIMEOUT_S=2",
                "FILE_MCP_STORAGE_TLS_INSECURE=false",
                "FILE_MCP_STORAGE_TLS_CA_BUNDLE=",
                "FILE_MCP_CONVERSION_TIMEOUT_S=10",
                "FILE_MCP_CONVERSION_MAX_INPUT_MB=20",
                "FILE_MCP_SNAPSHOT_RETENTION_DAYS=30",
                "FILE_MCP_SNAPSHOT_RETENTION_COUNT=-1",
                "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB=-1",
                "FILE_MCP_STORAGE_BACKEND=ftp",
                "FILE_MCP_S3_ENDPOINT=",
                "FILE_MCP_S3_BUCKET=",
                "FILE_MCP_S3_REGION=",
                "FILE_MCP_S3_ACCESS_KEY=",
                "FILE_MCP_S3_SECRET_KEY=",
                "FILE_MCP_S3_PREFIX=",
                "FILE_MCP_WEBDAV_BASE_URL=",
                "FILE_MCP_WEBDAV_USERNAME=",
                "FILE_MCP_WEBDAV_PASSWORD=",
                # Use a reserved TEST-NET address to guarantee connect failure.
                "FILE_MCP_FTP_HOST=192.0.2.10",
                "FILE_MCP_FTP_PORT=21",
                "FILE_MCP_FTP_USERNAME=nobody",
                "FILE_MCP_FTP_PASSWORD=nobody",
                "FILE_MCP_FTP_BASE_DIR=/",
                "FILE_MCP_FTP_USE_TLS=false",
                "FILE_MCP_GDRIVE_USER_EMAIL=",
                "FILE_MCP_GDRIVE_FOLDER_ID=",
                "FILE_MCP_GDRIVE_FOLDER_URL=",
                "FILE_MCP_GDRIVE_CLIENT_ID=",
                "FILE_MCP_GDRIVE_CLIENT_SECRET=",
                "FILE_MCP_GDRIVE_REFRESH_TOKEN=",
                "FILE_MCP_GDRIVE_ACCESS_TOKEN=",
                "FILE_MCP_GDRIVE_REDIRECT_URI=urn:ietf:wg:oauth:2.0:oob",
                "FILE_MCP_GDRIVE_TOKEN_URI=https://oauth2.googleapis.com/token",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "file_mcp_server",
        "serve",
        "--profile",
        "default",
        "--env-path",
        str(env_path),
        "--config-path",
        str(config_path),
        "--defaults-path",
        str(defaults_path),
        "--pidfile",
        str(pidfile),
        "--force-pidfile",
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert proc.returncode == 76
