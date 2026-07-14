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

"""W28A-889-A-R2 — /auth/status best-effort IDAM capability probe.

The shared @cloud-dog/idam Users page calls /auth/status (and the legacy
/api/auth/status alias). Before this fix file-mcp returned 404, which the Users
page surfaced as a "Not Found" error banner. The handler must:
  * return 401 for an unauthenticated caller;
  * authenticate X-API-Key and Bearer carriers without escalating a
    file-scoped key to system administrator;
  * report system-admin capability for the real cookie-authenticated admin.

Runs against a live base URL (E2E_BASE_URL, default preprod filemcpserver0).
"""

from __future__ import annotations

import httpx
import pytest

from tests.env_runtime import env_get


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-023")
def test_auth_status_unauth_denied_authed_capability() -> None:
    base_url = env_get("E2E_BASE_URL").strip()
    api_key = env_get("E2E_FILE_MCP_API_KEY").strip()
    web_username = env_get("E2E_FILE_MCP_WEB_USERNAME").strip()
    web_password = env_get("E2E_FILE_MCP_WEB_PASSWORD").strip()
    if not all((base_url, api_key, web_username, web_password)):
        pytest.fail(
            "E2E_BASE_URL, E2E_FILE_MCP_API_KEY, "
            "E2E_FILE_MCP_WEB_USERNAME and E2E_FILE_MCP_WEB_PASSWORD are required"
        )

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        # §0C: unauthenticated principal probe is denied (never an admin principal)
        for path in ("/auth/status", "/api/auth/status"):
            r = client.get(path)
            assert r.status_code == 401, f"unauth {path} must be 401, got {r.status_code}: {r.text[:120]}"
            assert '"is_system_admin": true' not in r.text and '"*"' not in r.text

        # File MCP is API-key authenticated. Both supported carriers must
        # resolve to the same authenticated capability response.
        carrier_capabilities = []
        for headers in (
            {"Authorization": f"Bearer {api_key}"},
            {"X-API-Key": api_key},
        ):
            for path in ("/auth/status", "/api/auth/status"):
                r = client.get(path, headers=headers)
                assert r.status_code == 200, (
                    f"authed {path} must be 200, got {r.status_code}: {r.text[:120]}"
                )
                body = r.json()
                assert body.get("authenticated") is True
                assert body.get("is_system_admin") is False
                assert body.get("username")
                permissions = body.get("permissions") or []
                assert "*" not in permissions and "admin:*" not in permissions
                carrier_capabilities.append(
                    (
                        path,
                        body.get("is_system_admin"),
                        tuple(sorted(permissions)),
                    )
                )

        assert carrier_capabilities[0:2] == carrier_capabilities[2:4]

        assert client.get(
            "/auth/status", headers={"X-API-Key": "invalid"}
        ).status_code == 401
        assert client.get(
            "/auth/status",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-API-Key": "conflicting-invalid",
            },
        ).status_code == 401

        login = client.post(
            "/auth/login",
            json={"username": web_username, "password": web_password},
        )
        assert login.status_code == 200, login.text[:120]
        for path in ("/auth/status", "/api/auth/status"):
            cookie_status = client.get(path)
            assert cookie_status.status_code == 200, cookie_status.text[:120]
            body = cookie_status.json()
            assert body.get("authenticated") is True
            assert body.get("is_system_admin") is True
            assert body.get("username") == web_username
