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

"""Integration test for CFG-06 A2A config-change broadcast.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Drives a real admin CRUD workflow against a running file-mcp
    server and asserts that the resulting ConfigChangeEvents appear at
    ``/a2a/events/history`` with the expected shape.
Requirements: CFG-06, FR1.23.
Tasks: W28A-1002-APPLY-A.
Architecture: 5. Tool Interface, SA1 API Kit integration.
Tests: IT_CFG06_A2AEvents.
"""


from __future__ import annotations
import pytest

import json
from pathlib import Path
from urllib.request import Request, urlopen

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
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-1.23")


def test_it_cfg06_admin_crud_publishes_events_to_a2a_events_history(
    tmp_path: Path,
) -> None:
    """A full admin CRUD cycle publishes CFG-06 events to /a2a/events/history."""
    port = pick_free_port()
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

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

        # 1) History is reachable from a cold start.
        status, payload = _json_request(
            method="GET", url=f"{base_url}/a2a/events/history"
        )
        assert status == 200
        assert "events" in payload
        initial_count = len(payload["events"])

        # 2) Create a user — expect a CFG-06 event.
        status, user_resp = _json_request(
            method="POST",
            url=f"{base_url}/admin/users",
            payload={"username": "cfg06-user", "display_name": "CFG-06 User"},
            headers=admin_headers,
        )
        assert status == 201
        user_id = str(user_resp["user"]["id"])

        # 3) Create an API key for that user — expect a second event.
        status, key_resp = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys",
            payload={
                "user_id": user_id,
                "label": "cfg06-key",
                "scopes": ["profile:default"],
            },
            headers=admin_headers,
        )
        assert status == 201
        api_key_id = str(key_resp["api_key"]["id"])

        # 4) Revoke the key — expect a third event.
        status, _ = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys/{api_key_id}/revoke",
            headers=admin_headers,
        )
        assert status == 200

        # 5) Delete the user — expect a fourth event.
        status, _ = _json_request(
            method="DELETE",
            url=f"{base_url}/admin/users/{user_id}",
            headers=admin_headers,
        )
        assert status == 200

        # 6) Assert all four events appear in /a2a/events/history.
        status, history = _json_request(
            method="GET",
            url=f"{base_url}/a2a/events/history?limit=100",
        )
        assert status == 200
        events = history["events"]
        new_events = events[initial_count:]
        # We expect at least these four actions in order.
        recent_actions = [(e["resource"], e["action"]) for e in new_events]
        assert ("user", "create") in recent_actions
        assert ("api_key", "create") in recent_actions
        assert ("api_key", "revoke") in recent_actions
        assert ("user", "delete") in recent_actions

        # 7) Every event MUST carry service="file-mcp-server" + identifier set.
        for event in new_events:
            assert event["service"] == "file-mcp-server"
            assert event["identifier"]
            assert event["event_id"] > 0
            assert event["timestamp"]

        # 8) No raw secret material leaks through api_key events.
        for event in new_events:
            if event["resource"] == "api_key":
                for payload_key in ("before", "after"):
                    inner = event.get(payload_key) or {}
                    if isinstance(inner, dict):
                        assert "api_key" not in inner
                        assert "secret" not in inner
                        assert "token" not in inner
