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

import asyncio
import os
from pathlib import Path
import uuid
from typing import Mapping

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import pick_free_port, running_server, wait_for_health


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _get(env: Mapping[str, str], key: str, default: str = "") -> str:
    value = env.get(key, "").strip()
    return value if value else default


def _require(env: Mapping[str, str], key: str) -> str:
    value = _get(env, key)
    if not value:
        raise RuntimeError(f"Missing required env var: {key}")
    return value


def _merged_env() -> dict[str, str]:
    repo_root = Path.cwd()
    merged: dict[str, str] = {}
    for candidate in (repo_root / "private" / "env-remote-storage", repo_root / "private" / "env-google-drive"):
        if candidate.exists():
            merged.update(_parse_env_file(candidate))
    merged.update(dict(os.environ))
    return merged


def test_google_drive_backend_end_to_end_live(tmp_path: Path) -> None:
    if os.getenv("FILE_MCP_RUN_GOOGLE_LIVE_TESTS", "0") != "1":
        pytest.skip("Set FILE_MCP_RUN_GOOGLE_LIVE_TESTS=1 to run live Google Drive integration tests")

    env_ctx = _merged_env()
    required = [
        "FILE_MCP_API_KEY_PRIMARY",
        "FILE_MCP_GDRIVE_CLIENT_ID",
        "FILE_MCP_GDRIVE_CLIENT_SECRET",
    ]
    missing = [key for key in required if not _get(env_ctx, key)]
    if missing:
        pytest.skip(f"Missing required Google live env vars: {', '.join(missing)}")
    if not (_get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_ID") or _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_URL")):
        pytest.skip("Missing FILE_MCP_GDRIVE_FOLDER_ID or FILE_MCP_GDRIVE_FOLDER_URL")
    if not (_get(env_ctx, "FILE_MCP_GDRIVE_REFRESH_TOKEN") or _get(env_ctx, "FILE_MCP_GDRIVE_ACCESS_TOKEN")):
        pytest.skip("Missing FILE_MCP_GDRIVE_REFRESH_TOKEN or FILE_MCP_GDRIVE_ACCESS_TOKEN")

    port = pick_free_port()
    run_id = uuid.uuid4().hex[:12]
    repo_root = Path.cwd()
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_path = repo_root / "private" / "env-remote-storage"

    if not env_path.exists():
        raise RuntimeError(f"Missing required env file: {env_path}")

    extra_env: dict[str, str] = {
        "FILE_MCP_HTTP_PORT": str(port),
        "FILE_MCP_STORAGE_BACKEND": "google_drive",
        "FILE_MCP_ROOT": "/",
        "FILE_MCP_AUDIT_LOG": "./working/remote-storage/audit.google-drive.log.jsonl",
        "FILE_MCP_SERVER_LOG": "./working/remote-storage/server.google-drive.log",
        "FILE_MCP_SNAPSHOT_DIR": "./working/remote-storage/snapshots.google-drive",
        "FILE_MCP_SNAPSHOT_RETENTION_DAYS": _get(env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_DAYS", "30"),
        "FILE_MCP_SNAPSHOT_RETENTION_COUNT": _get(env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_COUNT", "-1"),
        "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB": _get(env_ctx, "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB", "-1"),
        "FILE_MCP_STORAGE_TIMEOUT_S": _get(env_ctx, "FILE_MCP_STORAGE_TIMEOUT_S", "30"),
        "FILE_MCP_SEARCH_TIMEOUT_S": _get(env_ctx, "FILE_MCP_SEARCH_TIMEOUT_S", "30"),
        "FILE_MCP_GDRIVE_USER_EMAIL": _get(env_ctx, "FILE_MCP_GDRIVE_USER_EMAIL", ""),
        "FILE_MCP_GDRIVE_FOLDER_ID": _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_ID", ""),
        "FILE_MCP_GDRIVE_FOLDER_URL": _get(env_ctx, "FILE_MCP_GDRIVE_FOLDER_URL", ""),
        "FILE_MCP_GDRIVE_CLIENT_ID": _require(env_ctx, "FILE_MCP_GDRIVE_CLIENT_ID"),
        "FILE_MCP_GDRIVE_CLIENT_SECRET": _require(env_ctx, "FILE_MCP_GDRIVE_CLIENT_SECRET"),
        "FILE_MCP_GDRIVE_REFRESH_TOKEN": _get(env_ctx, "FILE_MCP_GDRIVE_REFRESH_TOKEN", ""),
        "FILE_MCP_GDRIVE_ACCESS_TOKEN": _get(env_ctx, "FILE_MCP_GDRIVE_ACCESS_TOKEN", ""),
        "FILE_MCP_GDRIVE_REDIRECT_URI": _get(env_ctx, "FILE_MCP_GDRIVE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob"),
        "FILE_MCP_GDRIVE_TOKEN_URI": _get(env_ctx, "FILE_MCP_GDRIVE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    }

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
                    headers={"Authorization": f"Bearer {_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}"},
                )
            ) as client:
                base = f"/it-google-{run_id}"
                path = f"{base}/hello.txt"

                await client.call_tool("create_dir", {"path": base, "parents": True, "exist_ok": True})
                await client.call_tool("write_file", {"path": path, "content": f"hello google {run_id}\n"})
                read = await client.call_tool("read_file", {"path": path})
                text = "".join(getattr(item, "text", "") for item in read.content)
                assert f"hello google {run_id}" in text

                await client.call_tool(
                    "json_set_file",
                    {"path": f"{base}/data.json", "json_path": "/run_id", "value": run_id, "dry_run": False},
                )
                await client.call_tool(
                    "search_content",
                    {"query": run_id, "max_depth": 3, "timeout_s": 10, "max_results": 5},
                )
                status = await client.call_tool("backend_status", {})
                payload = status.data if hasattr(status, "data") else {}
                assert payload.get("active_backend") == "google_drive"

                with pytest.raises(Exception) as excinfo:
                    await client.call_tool("chmod_path", {"path": path, "mode": "0644"})
                assert "Not supported for backend" in str(excinfo.value)

                await client.call_tool("delete_file", {"path": path, "missing_ok": True})

        asyncio.run(_flow())
