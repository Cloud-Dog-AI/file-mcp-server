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

"""Application-level profile lifecycle workflow test.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Validates full profile lifecycle across admin API and MCP tools.
Requirements: FR1.36, FR1.46
Tasks: W28A-255
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: AT_PROFILE_LIFECYCLE
"""


from __future__ import annotations
import pytest

import asyncio
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
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

    try:
        with urlopen(request, timeout=5.0) as response:
            content = response.read().decode("utf-8").strip()
            parsed = json.loads(content) if content else {}
            return int(response.status), parsed if isinstance(parsed, dict) else {}
    except HTTPError as exc:
        content = exc.read().decode("utf-8").strip()
        parsed: dict[str, Any]
        if content:
            try:
                decoded = json.loads(content)
                parsed = decoded if isinstance(decoded, dict) else {"raw": decoded}
            except Exception:
                parsed = {"raw": content}
        else:
            parsed = {}
        return int(exc.code), parsed


def _result_payload(result: Any) -> dict[str, Any]:
    content = getattr(result, "content", [])
    text = "".join(str(getattr(item, "text", "")) for item in content).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {"text": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


async def _call_tool(client: Client, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    payload = _result_payload(result)
    if payload.get("ok") is False:
        raise RuntimeError(f"Tool '{tool}' failed: {payload}")
    return payload


def _is_present(matches: list[Any], expected_path: str) -> bool:
    expected = expected_path.strip()
    expected_name = Path(expected).name
    for item in matches:
        value = str(item).strip()
        if not value:
            continue
        if value == expected or value.endswith(expected_name):
            return True
    return False
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_profile_lifecycle_project_folder_with_dated_content(tmp_path: Path) -> None:
    """Validate API+MCP profile lifecycle, scoping, search, and teardown."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    profile_name = "test-project-w28a255"
    username = f"w28a255-admin-{stamp}"

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    base_root = tmp_path / "workspace"
    base_root.mkdir(parents=True, exist_ok=True)
    profile_root = base_root / "projects" / profile_name
    profile_root.mkdir(parents=True, exist_ok=True)
    outside_root = tmp_path / "outside"
    outside_root.mkdir(parents=True, exist_ok=True)

    port = pick_free_port()
    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        runtime_dir,
        port=port,
        root_dir=base_root,
        api_keys=["bootstrap-key"],
        extra_env_lines=[
            "FILE_MCP_ADMIN_UI_ENABLED=true",
            "FILE_MCP_ADMIN_UI_TOKEN=admin-token",
        ],
    )

    base_url = f"http://127.0.0.1:{port}"
    admin_headers = {"x-admin-token": "admin-token"}

    repo_root = project_root(Path(__file__))
    server_kwargs = {
        "repo_root": repo_root,
        "defaults_path": defaults_path,
        "config_path": config_path,
        "env_path": env_path,
        "pidfile": pidfile,
        "extra_env": {
            "FILE_MCP_ADMIN_UI_ENABLED": "true",
            "FILE_MCP_ADMIN_UI_TOKEN": "admin-token",
        },
    }

    with running_server(**server_kwargs):
        health = wait_for_health(f"{base_url}/health", timeout_s=20.0)
        assert health.get("status") == "ok"

        stale_status, _ = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/profiles/{profile_name}",
            headers=admin_headers,
        )
        assert stale_status in {200, 404}

        user_status, user_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/users",
            payload={"username": username, "display_name": "W28A-255 Admin"},
            headers=admin_headers,
        )
        assert user_status == 201
        user_id = str(user_payload["user"]["id"])

        key_status, key_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys",
            payload={
                "user_id": user_id,
                "label": "w28a255-profile-key",
                "profile_name": profile_name,
                "scopes": [f"profile:{profile_name}"],
            },
            headers=admin_headers,
        )
        assert key_status == 201
        api_key_secret = str(key_payload["api_key"]["secret"])

        profile_status, profile_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/profiles",
            payload={
                "name": profile_name,
                "root": str(profile_root),
                "backend": "local",
            },
            headers=admin_headers,
        )
        assert profile_status == 201
        assert profile_payload.get("ok") is True

        profile_get_status, profile_get_payload = _json_request(
            method="GET",
            url=f"{base_url}/admin/profiles/{profile_name}",
            headers=admin_headers,
        )
        assert profile_get_status == 200
        roots = profile_get_payload.get("profile", {}).get("roots", [])
        assert str(profile_root) in roots

    date_dir = date.today().isoformat()
    scoped_folder = str(profile_root / date_dir)
    markdown_path = str(profile_root / date_dir / "test-content.md")
    second_path = str(profile_root / date_dir / "supplement.txt")
    outside_path = str(outside_root / "blocked.txt")

    with running_server(**server_kwargs):
        health = wait_for_health(f"{base_url}/health", timeout_s=20.0)
        assert health.get("status") == "ok"

        async def _workflow() -> None:
            transport = StreamableHttpTransport(
                f"{base_url}/mcp?profile={profile_name}",
                headers={
                    "Authorization": f"Bearer {api_key_secret}",
                    "X-File-MCP-Profile": profile_name,
                },
            )
            async with Client(transport) as client:
                tools = await client.list_tools()
                available = {str(tool.name or "") for tool in tools}
                for required in {
                    "create_dir",
                    "write_file",
                    "read_file",
                    "search_paths",
                    "delete_file",
                }:
                    assert required in available

                await _call_tool(
                    client,
                    "create_dir",
                    {"path": scoped_folder, "parents": True, "exist_ok": True},
                )

                await _call_tool(
                    client,
                    "write_file",
                    {
                        "path": markdown_path,
                        "content": (
                            "# W28A-255 Test Content\n\n"
                            "Initial markdown content for lifecycle verification.\n"
                        ),
                        "overwrite": True,
                    },
                )

                await _call_tool(
                    client,
                    "write_file",
                    {
                        "path": second_path,
                        "content": "Secondary file for lifecycle verification.\n",
                        "overwrite": True,
                    },
                )

                markdown_read = await _call_tool(client, "read_file", {"path": markdown_path})
                markdown_text = str(
                    markdown_read.get("content") or markdown_read.get("text") or ""
                )
                await _call_tool(
                    client,
                    "write_file",
                    {
                        "path": markdown_path,
                        "content": markdown_text + "\nAppend line for W28A-255.\n",
                        "overwrite": True,
                    },
                )

                markdown_verify = await _call_tool(
                    client, "read_file", {"path": markdown_path}
                )
                verify_text = str(
                    markdown_verify.get("content") or markdown_verify.get("text") or ""
                )
                assert "Append line for W28A-255" in verify_text

                markdown_search = await _call_tool(
                    client,
                    "search_paths",
                    {"query": "test-content.md"},
                )
                markdown_matches = markdown_search.get("matches") or []
                assert _is_present(markdown_matches, markdown_path)

                full_search = await _call_tool(
                    client,
                    "search_paths",
                    {"query": date_dir},
                )
                full_matches = full_search.get("matches") or []
                assert _is_present(full_matches, markdown_path)
                assert _is_present(full_matches, second_path)

                try:
                    await _call_tool(
                        client,
                        "write_file",
                        {
                            "path": outside_path,
                            "content": "scope breach",
                            "overwrite": True,
                        },
                    )
                except Exception:
                    pass
                else:
                    raise AssertionError(
                        "Profile scope enforcement failed: write outside profile root succeeded"
                    )

                await _call_tool(
                    client,
                    "delete_file",
                    {"path": markdown_path, "missing_ok": False},
                )
                await _call_tool(
                    client,
                    "delete_file",
                    {"path": second_path, "missing_ok": False},
                )
                try:
                    await _call_tool(
                        client,
                        "delete_file",
                        {"path": scoped_folder, "missing_ok": False},
                    )
                except Exception:
                    shutil.rmtree(scoped_folder)

        asyncio.run(_workflow())

        assert not Path(markdown_path).exists()
        assert not Path(second_path).exists()
        assert not Path(scoped_folder).exists()
        assert not Path(outside_path).exists()

        delete_user_status, delete_user_payload = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/users/{user_id}",
            headers=admin_headers,
        )
        assert delete_user_status == 200
        assert delete_user_payload.get("result", {}).get("deleted") is True

        delete_profile_status, delete_profile_payload = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/profiles/{profile_name}",
            headers=admin_headers,
        )
        assert delete_profile_status == 200
        assert delete_profile_payload.get("deleted") is True

        profile_404_status, _ = _json_request(
            method="GET",
            url=f"{base_url}/admin/profiles/{profile_name}",
            headers=admin_headers,
        )
        assert profile_404_status == 404
