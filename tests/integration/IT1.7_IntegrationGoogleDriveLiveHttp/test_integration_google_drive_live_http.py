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

"""Live Google Drive backend integration tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: End-to-end MCP tool validation against a real Google Drive folder.
Requirements: FR1.26, FR1.29, FR1.30, FR1.31, FR1.32
Tasks: T23
Architecture: 9.2 Google Drive Backend
Tests: IT1.15
"""

from __future__ import annotations

from tests.env_runtime import env_get

import asyncio
import os
from pathlib import Path
import uuid
from typing import Mapping

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
)
from tests.remote_env_helpers import (
    file_mcp_env_values,
    merged_remote_env,
    write_env_file,
)

def _gdrive_live_enabled() -> bool:
    value = env_get("FILE_MCP_RUN_GDRIVE_LIVE_TEST", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get(env: Mapping[str, str], key: str, default: str = "") -> str:
    value = env.get(key, "").strip()
    return value if value else default


def _require(env: Mapping[str, str], key: str) -> str:
    value = _get(env, key)
    if not value:
        raise RuntimeError(f"Missing required env var: {key}")
    return value


@pytest.mark.skipif(
    os.environ.get("FILE_MCP_RUN_GDRIVE_LIVE_TEST") != "1",
    reason="GDrive deferred: requires web OAuth interface (W28A-121)",
)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding
def test_google_drive_backend_end_to_end_live(tmp_path: Path) -> None:
    if not _gdrive_live_enabled():
        pytest.fail(
            "Set FILE_MCP_RUN_GDRIVE_LIVE_TEST=1 to run live GDrive test; "
            "GDrive OAuth not available"
        )

    repo_root = Path.cwd()
    env_ctx = merged_remote_env(repo_root, include_google=True)
    required = [
        "FILE_MCP_API_KEY_PRIMARY",
        "FILE_MCP_GDRIVE_CLIENT_ID",
        "FILE_MCP_GDRIVE_CLIENT_SECRET",
    ]
    missing = [key for key in required if not _get(env_ctx, key)]
    if missing:
        pytest.fail(f"Missing required Google live env vars: {', '.join(missing)}")
    if not (
        _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_ID")
        or _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_URL")
    ):
        pytest.fail("Missing FILE_MCP_GDRIVE_FOLDER_ID or FILE_MCP_GDRIVE_FOLDER_URL")
    if not (
        _get(env_ctx, "FILE_MCP_GDRIVE_REFRESH_TOKEN")
        or _get(env_ctx, "FILE_MCP_GDRIVE_ACCESS_TOKEN")
    ):
        pytest.fail(
            "Missing FILE_MCP_GDRIVE_REFRESH_TOKEN or FILE_MCP_GDRIVE_ACCESS_TOKEN"
        )

    port = pick_free_port()
    run_id = uuid.uuid4().hex[:12]
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_path = tmp_path / "google-live.env"
    runtime_env = file_mcp_env_values(env_ctx)

    extra_env: dict[str, str] = {
        "FILE_MCP_HTTP_PORT": str(port),
        "FILE_MCP_API_KEY_PRIMARY": _require(env_ctx, "FILE_MCP_API_KEY_PRIMARY"),
        "FILE_MCP_AUTH_HEADER_NAME": _get(
            env_ctx, "FILE_MCP_AUTH_HEADER_NAME", "Authorization"
        ),
        "FILE_MCP_AUTH_HEADER_SCHEME": _get(
            env_ctx, "FILE_MCP_AUTH_HEADER_SCHEME", "Bearer"
        ),
        "FILE_MCP_STORAGE_BACKEND": "google_drive",
        "CLOUD_DOG__PROFILES__DEFAULT__STORAGE__BACKEND": "google_drive",
        "FILE_MCP_ROOT": "/",
        "FILE_MCP_AUDIT_LOG": "./working/remote-storage/audit.google-drive.log.jsonl",
        "FILE_MCP_SERVER_LOG": "./working/remote-storage/server.google-drive.log",
        "FILE_MCP_SNAPSHOT_DIR": "./working/remote-storage/snapshots.google-drive",
        "FILE_MCP_SNAPSHOT_RETENTION_DAYS": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_DAYS", "30"
        ),
        "FILE_MCP_SNAPSHOT_RETENTION_COUNT": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_COUNT", "-1"
        ),
        "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB", "-1"
        ),
        "FILE_MCP_STORAGE_TIMEOUT_S": _get(env_ctx, "FILE_MCP_STORAGE_TIMEOUT_S", "30"),
        "FILE_MCP_SEARCH_TIMEOUT_S": _get(env_ctx, "FILE_MCP_SEARCH_TIMEOUT_S", "30"),
        "FILE_MCP_GDRIVE_USER_EMAIL": _get(env_ctx, "FILE_MCP_GDRIVE_USER_EMAIL", ""),
        "FILE_MCP_GDRIVE_FOLDER_ID": _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_ID", ""),
        "FILE_MCP_GDRIVE_FOLDER_URL": _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_URL", ""),
        "FILE_MCP_GDRIVE_CLIENT_ID": _require(env_ctx, "FILE_MCP_GDRIVE_CLIENT_ID"),
        "FILE_MCP_GDRIVE_CLIENT_SECRET": _require(
            env_ctx, "FILE_MCP_GDRIVE_CLIENT_SECRET"
        ),
        "FILE_MCP_GDRIVE_REFRESH_TOKEN": _get(
            env_ctx, "FILE_MCP_GDRIVE_REFRESH_TOKEN", ""
        ),
        "FILE_MCP_GDRIVE_ACCESS_TOKEN": _get(
            env_ctx, "FILE_MCP_GDRIVE_ACCESS_TOKEN", ""
        ),
        "FILE_MCP_GDRIVE_REDIRECT_URI": _get(
            env_ctx, "FILE_MCP_GDRIVE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob"
        ),
        "FILE_MCP_GDRIVE_TOKEN_URI": _get(
            env_ctx, "FILE_MCP_GDRIVE_TOKEN_URI", "https://oauth2.googleapis.com/token"
        ),
    }
    runtime_env.update(extra_env)
    write_env_file(env_path, runtime_env)

    Path("./working/remote-storage").mkdir(parents=True, exist_ok=True)
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=tmp_path / "google-drive.pid",
        extra_env=extra_env,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=20.0)

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={
                        "Authorization": f"Bearer {_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}"
                    },
                )
            ) as client:
                base = f"/it-google-{run_id}"
                path = f"{base}/hello.txt"

                await client.call_tool(
                    "create_dir", {"path": base, "parents": True, "exist_ok": True}
                )
                await client.call_tool(
                    "write_file", {"path": path, "content": f"hello google {run_id}\n"}
                )
                read = await client.call_tool("read_file", {"path": path})
                text = "".join(getattr(item, "text", "") for item in read.content)
                assert f"hello google {run_id}" in text

                await client.call_tool(
                    "write_file",
                    {"path": f"{base}/data.json", "content": "{}\n"},
                )
                await client.call_tool(
                    "json_set_file",
                    {
                        "path": f"{base}/data.json",
                        "json_path": "/run_id",
                        "value": run_id,
                        "dry_run": False,
                    },
                )
                await client.call_tool(
                    "search_content",
                    {
                        "query": run_id,
                        "max_depth": 3,
                        "timeout_s": 10,
                        "max_results": 5,
                    },
                )
                status = await client.call_tool("backend_status", {})
                payload = status.data if hasattr(status, "data") else {}
                assert payload.get("active_backend") == "google_drive"

                with pytest.raises(Exception) as excinfo:
                    await client.call_tool("chmod_path", {"path": path, "mode": "0644"})
                assert "Not supported for backend" in str(excinfo.value)

                await client.call_tool(
                    "delete_file", {"path": path, "missing_ok": True}
                )

        asyncio.run(_flow())
