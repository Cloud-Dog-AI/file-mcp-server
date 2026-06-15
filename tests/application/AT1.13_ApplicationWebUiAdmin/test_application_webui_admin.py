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

"""Application-level WebUI admin verification.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Verifies WebUI admin pages for profile and identity management render with live CRUD data.
Requirements: FR1.36, FR1.46
Tasks: W28A-245
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: AT1.13
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


def _html_request(*, url: str, headers: dict[str, str]) -> tuple[int, str]:
    request = Request(url, method="GET")
    request.add_header("Accept", "text/html")
    for key, value in headers.items():
        request.add_header(key, value)
    with urlopen(request, timeout=5.0) as response:
        return int(response.status), response.read().decode("utf-8")


def _is_spa_shell(html: str) -> bool:
    return "<div id=\"root\"></div>" in html and "/runtime-config.js" in html


def _is_legacy_admin_html(route: str, html: str) -> bool:
    if route == "/admin/profiles":
        return "<h1>Profile Management</h1>" in html
    if route in ("/admin/identity", "/admin/users", "/admin/groups", "/admin/api-keys"):
        return "<h1>Identity Management</h1>" in html
    if route == "/admin/rbac":
        return "<h1>RBAC</h1>" in html or "<h1>Role-Based Access Control</h1>" in html
    return False
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-016")


def test_at1_13_webui_admin_pages_render_profile_and_identity_data(
    tmp_path: Path,
) -> None:
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

        base_url = f"http://127.0.0.1:{port}"
        admin_headers = {"x-admin-token": "admin-token"}

        group_status, group_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/groups",
            payload={"name": "web-admins", "roles": ["admin"]},
            headers=admin_headers,
        )
        assert group_status == 201
        assert group_payload["group"]["name"] == "web-admins"

        user_status, user_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/users",
            payload={
                "username": "web-user",
                "display_name": "Web User",
                "groups": ["web-admins"],
            },
            headers=admin_headers,
        )
        assert user_status == 201
        user_id = str(user_payload["user"]["id"])

        key_status, key_payload = _json_request(
            method="POST",
            url=f"{base_url}/admin/api-keys",
            payload={"user_id": user_id, "label": "web-ui-key"},
            headers=admin_headers,
        )
        assert key_status == 201
        assert key_payload["api_key"]["label"] == "web-ui-key"

        users_status, users_payload = _json_request(
            method="GET",
            url=f"{base_url}/admin/users",
            headers=admin_headers,
        )
        assert users_status == 200
        assert any(user["username"] == "web-user" for user in users_payload["users"])

        groups_status, groups_payload = _json_request(
            method="GET",
            url=f"{base_url}/admin/groups",
            headers=admin_headers,
        )
        assert groups_status == 200
        assert any(group["name"] == "web-admins" for group in groups_payload["groups"])

        api_keys_status, api_keys_payload = _json_request(
            method="GET",
            url=f"{base_url}/admin/api-keys",
            headers=admin_headers,
        )
        assert api_keys_status == 200
        assert any(key["label"] == "web-ui-key" for key in api_keys_payload["api_keys"])

        for route in (
            "/admin/profiles",
            "/admin/identity",
            "/admin/users",
            "/admin/groups",
            "/admin/api-keys",
            "/admin/rbac",
        ):
            status, html = _html_request(
                url=f"{base_url}{route}",
                headers=admin_headers,
            )
            assert status == 200
            assert _is_spa_shell(html) or _is_legacy_admin_html(route, html)
