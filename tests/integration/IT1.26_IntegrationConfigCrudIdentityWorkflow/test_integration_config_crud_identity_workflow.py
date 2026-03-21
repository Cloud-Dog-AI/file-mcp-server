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

"""Integration workflow for config/user/key CRUD completion.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Validates user creation, API key issuance, profile creation, MCP file operations, and teardown.
Requirements: FR1.36, FR1.46
Tasks: W28A-245
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: IT1.26
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.request import Request, urlopen

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root


def _json_request(
    *,
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    body = b""
    merged_headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"
    if headers:
        merged_headers.update(headers)
    request = Request(url, data=body if payload is not None else None, method=method)
    for key, value in merged_headers.items():
        request.add_header(key, value)

    with urlopen(request, timeout=5.0) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
        return int(response.status), response_payload


def test_it1_26_user_key_profile_lifecycle_supports_mcp_file_operations(
    tmp_path: Path,
) -> None:
    port = pick_free_port()
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    profile_root = tmp_path / "profile-crud-scope"
    profile_root.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        runtime_dir,
        port=port,
        root_dir=root_dir,
        api_keys=["bootstrap-key"],
        extra_env_lines=[
            "FILE_MCP_ADMIN_UI_ENABLED=true",
            "FILE_MCP_ADMIN_UI_TOKEN=admin-token",
        ],
    )

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
        extra_env={
            "FILE_MCP_ADMIN_UI_ENABLED": "true",
            "FILE_MCP_ADMIN_UI_TOKEN": "admin-token",
        },
    ):
        health = wait_for_health(f"http://127.0.0.1:{port}/health")
        assert health["status"] == "ok"

        admin_headers = {"x-admin-token": "admin-token"}
        base_url = f"http://127.0.0.1:{port}"

        user_status, user_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/users",
            payload={"username": "workflow-user", "display_name": "Workflow User"},
            headers=admin_headers,
        )
        assert user_status == 201
        user_id = str(user_payload["user"]["id"])

        key_status, key_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys",
            payload={
                "user_id": user_id,
                "label": "workflow-key",
                "scopes": ["profile:default"],
            },
            headers=admin_headers,
        )
        assert key_status == 201
        api_key_id = str(key_payload["api_key"]["id"])
        api_key_secret = str(key_payload["api_key"]["secret"])

        profile_status, profile_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/profiles",
            payload={
                "name": "workflow-profile",
                "root": str(profile_root),
                "backend": "local",
            },
            headers=admin_headers,
        )
        assert profile_status == 201
        assert profile_payload["ok"] is True

        async def _mcp_roundtrip() -> None:
            transport = StreamableHttpTransport(
                f"{base_url}/mcp",
                headers={
                    "Authorization": f"Bearer {api_key_secret}",
                    "X-File-MCP-Profile": "default",
                },
            )
            async with Client(transport) as client:
                target_path = str(root_dir / "workflow.txt")
                await client.call_tool(
                    "write_file",
                    {
                        "path": target_path,
                        "content": "workflow-content",
                        "overwrite": True,
                    },
                )
                result = await client.call_tool("read_file", {"path": target_path})
                text = "\n".join(
                    item.text for item in result.content if hasattr(item, "text")
                )
                assert "workflow-content" in text

        asyncio.run(_mcp_roundtrip())

        revoke_status, revoke_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys/{api_key_id}/revoke",
            headers=admin_headers,
        )
        assert revoke_status == 200
        assert revoke_payload["api_key"]["is_active"] is False

        delete_user_status, delete_user_payload = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/users/{user_id}",
            headers=admin_headers,
        )
        assert delete_user_status == 200
        assert delete_user_payload["result"]["deleted"] is True

        delete_profile_status, delete_profile_payload = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/profiles/workflow-profile",
            headers=admin_headers,
        )
        assert delete_profile_status == 200
        assert delete_profile_payload["deleted"] is True
