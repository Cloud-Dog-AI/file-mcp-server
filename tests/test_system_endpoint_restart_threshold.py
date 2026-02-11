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


def test_server_exits_when_restart_threshold_reached(tmp_path: Path) -> None:
    repo_root = Path.cwd()
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_path = tmp_path / "env.restart-threshold"
    pidfile = tmp_path / "restart.pid"

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
                "FILE_MCP_CONVERSION_TIMEOUT_S=10",
                "FILE_MCP_CONVERSION_MAX_INPUT_MB=20",
                "FILE_MCP_SNAPSHOT_RETENTION_DAYS=30",
                "FILE_MCP_SNAPSHOT_RETENTION_COUNT=-1",
                "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB=-1",
                "FILE_MCP_STORAGE_BACKEND=ftp",
                # Use a reserved TEST-NET address to guarantee connect failure.
                "FILE_MCP_FTP_HOST=192.0.2.10",
                "FILE_MCP_FTP_PORT=21",
                "FILE_MCP_FTP_USERNAME=nobody",
                "FILE_MCP_FTP_PASSWORD=nobody",
                "FILE_MCP_FTP_BASE_DIR=/",
                "FILE_MCP_FTP_USE_TLS=false",
                "FILE_MCP_ENDPOINT_HEALTH_ENABLED=true",
                "FILE_MCP_ENDPOINT_HEALTH_CHECK_ON_STARTUP=true",
                "FILE_MCP_ENDPOINT_HEALTH_CHECK_ALL=false",
                "FILE_MCP_ENDPOINT_HEALTH_MAX_RETRIES=0",
                "FILE_MCP_ENDPOINT_HEALTH_RETRY_INTERVAL_S=1",
                "FILE_MCP_ENDPOINT_HEALTH_RETRY_WINDOW_S=60",
                "FILE_MCP_ENDPOINT_HEALTH_MAX_FAILURES_BEFORE_RESTART=1",
                "FILE_MCP_ENDPOINT_HEALTH_RECOVER_AFTER_S=30",
                "FILE_MCP_ENDPOINT_HEALTH_RESTART_ON_THRESHOLD=true",
                "FILE_MCP_ENDPOINT_HEALTH_RESTART_EXIT_CODE=76",
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
