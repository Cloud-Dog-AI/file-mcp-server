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

"""file-mcp-server — UT1.35: Thread-a flat WebUI login (admin / read-write / read-only).

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: PROGRAM-IDAM-RECOVERY-2 Thread a (lane a2, W28A-728-R4) — the simple
flat login that gets the file-mcp demo back. Locks:

  * the static UI shell (/runtime-config.js, the SPA /login route) is PUBLIC —
    an anonymous browser can load the login box;
  * the DATA surfaces (/auth/me, /api/*, /v1/*) stay auth-gated (anon -> 401);
  * /auth/login issues a flat-role session for each of the three accounts and
    /auth/me echoes the shared-idam-derived role + permissions;
  * a read-only session is denied write methods inline (403), never a 401 and
    never a blank UI; a read-write session is NOT pre-gated;
  * logout clears the session.

Permissions come from the ONE shared cloud_dog_idam guard (no per-service RBAC
fork) — see file_mcp_server/web_flat_roles.py.

Requirements: NF1.3, NF1.6
Tasks: W28A-728-R4
Tests: UT1.35
"""

from __future__ import annotations

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

import pytest
from fastapi.testclient import TestClient

from file_mcp_server.server import HealthCheckMiddleware
from file_mcp_server.web_flat_roles import (
    ADMIN_ROLE,
    READ_ONLY_ROLE,
    READ_WRITE_ROLE,
    role_can_write,
)

# Demo flat-role credentials (env-overridable CLOUD_DOG_WEB_LOGIN_*; defaults
# live in code so the three roles are demoable out of the box).
ACCOUNTS = {
    ADMIN_ROLE: ("admin", "OrangeRiverTable"),
    READ_WRITE_ROLE: ("read-write", "BlueRiverChair"),
    READ_ONLY_ROLE: ("read-only", "GreenRiverDesk"),
}

# Public static shell an anon browser must be able to load.
PUBLIC_STATIC = ("/runtime-config.js", "/login")
# Data surfaces that stay auth-gated for anon.
GATED_DATA = ("/auth/me", "/api/v1/profiles", "/v1/profiles")


async def _inner_api_app(scope, receive, send) -> None:
    """Stand-in for the cloud_dog_api_kit inner app.

    The real inner FastAPI app enforces auth on the data surfaces and returns
    401 for an unauthenticated caller. Model exactly that here so the anon->401
    contract is deterministic in a unit context (no live upstream): any request
    that reaches the inner app without an api-key/bearer is treated as
    unauthenticated -> 401.
    """
    headers = {
        (k.decode("latin-1").lower() if isinstance(k, bytes) else str(k).lower()): (
            v.decode("latin-1") if isinstance(v, bytes) else str(v)
        )
        for k, v in (scope.get("headers") or [])
    }
    has_auth = bool(headers.get("authorization") or headers.get("x-api-key"))
    if has_auth:
        body = b'{"ok": true}'
        status = 200
    else:
        body = b'{"detail": "Not authenticated"}'
        status = 401
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


@pytest.fixture()
def web_client() -> TestClient:
    # Use the repo's built ui/dist bundle (the same one the container ships) so
    # the public /login SPA route serves the real shell (200), not the "UI not
    # built" fallback. Clear any stale override so the default dist path resolves.
    runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
    mw = HealthCheckMiddleware(
        _inner_api_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )
    return TestClient(mw, raise_server_exceptions=False)


def _login(client: TestClient, role: str) -> "dict[str, str]":
    user, pw = ACCOUNTS[role]
    resp = client.post("/auth/login", json={"username": user, "password": pw})
    assert resp.status_code == 200, f"{role} login: {resp.status_code} {resp.text[:200]}"
    return {k: v for k, v in resp.cookies.items()}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_static_ui_is_public_for_anon(web_client: TestClient) -> None:
    # ASSERTION 1: the public static shell loads for an anonymous visitor.
    for path in PUBLIC_STATIC:
        resp = web_client.get(path)
        assert resp.status_code == 200, (
            f"anon {path} must be PUBLIC 200 (login box must load); "
            f"got {resp.status_code}: {resp.text[:160]}"
        )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_data_surfaces_gated_for_anon(web_client: TestClient) -> None:
    # ASSERTION 2: data surfaces stay auth-gated (anon -> 401).
    for path in GATED_DATA:
        resp = web_client.get(path)
        assert resp.status_code == 401, (
            f"anon {path} must be 401 (data stays auth-gated); "
            f"got {resp.status_code}: {resp.text[:160]}"
        )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_mcp_discovery_gated_for_anon(web_client: TestClient) -> None:
    resp = web_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 401, (
        f"anon POST /mcp tools/list must be 401; got {resp.status_code}: {resp.text[:160]}"
    )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_each_flat_role_logs_in_with_expected_role(web_client: TestClient) -> None:
    # ASSERTION 3: all three flat roles log in with the correct shared-guard perms.
    for role in (ADMIN_ROLE, READ_WRITE_ROLE, READ_ONLY_ROLE):
        cookies = _login(web_client, role)
        me = web_client.get("/auth/me", cookies=cookies)
        assert me.status_code == 200, me.text[:200]
        body = me.json()["user"]
        assert body["roles"] == [role], body
        perms = body["permissions"]
        if role == ADMIN_ROLE:
            assert perms == ["*"], perms
        else:
            assert "*" not in perms and len(perms) >= 1, perms
            # read-write carries write perms; read-only does not.
            has_write = any(p.endswith(".write") or p.endswith(":write") for p in perms)
            assert has_write is role_can_write(role), (role, perms)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_read_only_writes_are_denied_inline_403(web_client: TestClient) -> None:
    # ASSERTION 4: a read-only session's writes are denied inline (403), never a
    # 401 and never a blank UI.
    cookies = _login(web_client, READ_ONLY_ROLE)
    for method, path in (
        ("POST", "/api/v1/profiles"),
        ("PUT", "/v1/profiles/1"),
        ("PATCH", "/v1/profiles/1"),
        ("DELETE", "/v1/profiles/1"),
    ):
        resp = web_client.request(method, path, cookies=cookies, json={"name": "x"})
        assert resp.status_code == 403, (
            f"read-only {method.upper()} {path} must be 403-inline (not 401, not 200); "
            f"got {resp.status_code}: {resp.text[:160]}"
        )
        assert "read-only role" in resp.text, resp.text[:160]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_read_write_writes_are_not_pre_gated(web_client: TestClient) -> None:
    # A read-write session must NOT be blocked by the read-only write-gate; the
    # request reaches the data dispatch. The contract: it is NOT a 403 from the
    # flat-role gate.
    cookies = _login(web_client, READ_WRITE_ROLE)
    resp = web_client.post("/api/v1/profiles", cookies=cookies, json={"name": "x"})
    assert resp.status_code != 403 or "read-only role" not in resp.text, resp.text[:200]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_bad_credentials_rejected(web_client: TestClient) -> None:
    assert (
        web_client.post(
            "/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        web_client.post(
            "/auth/login", json={"username": "ghost", "password": "x"}
        ).status_code
        == 401
    )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("R4")


def test_logout_clears_session(web_client: TestClient) -> None:
    # ASSERTION 5: logout clears the session.
    cookies = _login(web_client, ADMIN_ROLE)
    assert web_client.get("/auth/me", cookies=cookies).status_code == 200
    web_client.post("/auth/logout", cookies=cookies)
    # After logout the in-memory token is dropped; reusing the stale cookie 401s.
    assert web_client.get("/auth/me", cookies=cookies).status_code == 401
