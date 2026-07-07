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

"""file-mcp-server — UT1.40 W28E-1863 fix-wave-a.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Two wave-3-audit defects.
  (1) Deep-link SPA-fallback (unauth): a logged-out *browser* (Accept:
      text/html) hard-navigating /admin, /admin/users, /google-drive-settings
      must receive the SPA shell (200 index.html, the client login gate) — NOT
      raw JSON 401/404 from uvicorn. API clients (non-HTML Accept) keep their
      401 JSON deny (W28C-1702 FM6 anon-gate contract preserved).
  (2) WSC-014 build identity: /version and /runtime-config.js must expose
      source_commit + build_date + container_digest + environment so the WebUI
      About page can render build provenance (PS-30 UI-R7.3).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

from file_mcp_server.server import HealthCheckMiddleware


async def _noop_app(scope, receive, send) -> None:  # pragma: no cover
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": b'{"error":"not found"}'})


def _run(mw, *, method, path, headers=None, body=b""):
    sent: list[dict] = []

    async def _go() -> None:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers or [],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            sent.append(message)

        await mw(scope, receive, send)

    asyncio.run(_go())
    return sent


def _status(sent):
    return sent[0]["status"]


def _content_type(sent):
    return dict(
        (k.decode(), v.decode()) for k, v in sent[0].get("headers", [])
    ).get("content-type", "")


def _body(sent) -> bytes:
    return b"".join(
        m.get("body", b"") for m in sent if m.get("type") == "http.response.body"
    )


BROWSER = [(b"accept", b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")]
API = [(b"accept", b"application/json")]

# Deep-link SPA routes that a logged-out browser may bookmark / hard-refresh.
DEEPLINK_SPA_PATHS = [
    "/admin",
    "/admin/users",
    "/admin/groups",
    "/admin/api-keys",
    "/admin/roles",
    "/admin/rbac",
    "/google-drive-settings",
    "/system/about",
    "/catalogue",
]

# The API surfaces that must still deny anonymous non-HTML clients (FM6 gate).
ANON_DENY_API_PATHS = [
    "/admin/users",
    "/admin/groups",
    "/admin/api-keys",
    "/admin/roles",
    "/google-drive-settings",
]


def _mw():
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
    return HealthCheckMiddleware(
        _noop_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")
def test_unauth_browser_deeplink_serves_spa_html() -> None:
    """Defect 1: logged-out browser deep-link -> SPA shell (200 text/html)."""
    mw = _mw()
    for path in DEEPLINK_SPA_PATHS:
        sent = _run(mw, method="GET", path=path, headers=BROWSER)  # no auth
        status = _status(sent)
        ctype = _content_type(sent)
        assert status == 200, f"unauth browser GET {path} -> {status}, expected 200 SPA"
        assert "text/html" in ctype, f"unauth browser GET {path} ct={ctype!r}"
        assert b"<!doctype html>" in _body(sent).lower(), f"{path} did not serve index.html"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")
def test_unauth_api_client_still_denied_json() -> None:
    """Defect 1 guard: API clients (non-HTML Accept) keep the 401 JSON deny."""
    mw = _mw()
    for path in ANON_DENY_API_PATHS:
        sent = _run(mw, method="GET", path=path, headers=API)  # no auth, JSON accept
        status = _status(sent)
        assert status == 401, f"unauth API GET {path} -> {status}, expected 401 JSON"
        assert b"client_id" not in _body(sent)


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-010.3")
def test_version_endpoint_exposes_build_identity() -> None:
    """Defect 2 (WSC-014): /version exposes commit/build/deploy identity."""
    runtime_env["FILE_MCP_SOURCE_COMMIT"] = "abc1234def5678901234567890abcdef12345678"
    runtime_env["FILE_MCP_SOURCE_BRANCH"] = "main"
    runtime_env["FILE_MCP_BUILD_DATE"] = "2026-07-07T12:00:00Z"
    runtime_env["FILE_MCP_CONTAINER_DIGEST"] = "sha256:deadbeefcafebabe"
    runtime_env["CLOUD_DOG_ENV"] = "preprod"
    try:
        mw = _mw()
        sent = _run(mw, method="GET", path="/version")
        assert _status(sent) == 200
        payload = json.loads(_body(sent).decode("utf-8"))
        assert payload["source_commit"] == "abc1234def5678901234567890abcdef12345678"
        assert payload["source_branch"] == "main"
        assert payload["build_date"] == "2026-07-07T12:00:00Z"
        assert payload["container_digest"] == "sha256:deadbeefcafebabe"
        assert payload["environment"] == "preprod"
        # legacy field DashboardPage VersionInfo already reads
        assert payload["commit"] == payload["source_commit"]
        assert payload["version"]
    finally:
        for key in (
            "FILE_MCP_SOURCE_COMMIT",
            "FILE_MCP_SOURCE_BRANCH",
            "FILE_MCP_BUILD_DATE",
            "FILE_MCP_CONTAINER_DIGEST",
            "CLOUD_DOG_ENV",
        ):
            runtime_env.pop(key, None)


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-010.3")
def test_runtime_config_exposes_build_identity() -> None:
    """Defect 2: /runtime-config.js exposes APP_COMMIT / APP_BUILD_DATE / etc."""
    runtime_env["FILE_MCP_SOURCE_COMMIT"] = "abc1234def5678901234567890abcdef12345678"
    runtime_env["FILE_MCP_BUILD_DATE"] = "2026-07-07T12:00:00Z"
    runtime_env["FILE_MCP_CONTAINER_DIGEST"] = "sha256:deadbeefcafebabe"
    runtime_env["CLOUD_DOG_ENV"] = "preprod"
    try:
        mw = _mw()
        sent = _run(mw, method="GET", path="/runtime-config.js")
        assert _status(sent) == 200
        script = _body(sent).decode("utf-8")
        assert '"APP_COMMIT": "abc1234def5678901234567890abcdef12345678"' in script
        assert '"APP_BUILD_DATE": "2026-07-07T12:00:00Z"' in script
        assert '"APP_CONTAINER_DIGEST": "sha256:deadbeefcafebabe"' in script
        assert '"APP_ENV": "preprod"' in script
    finally:
        for key in (
            "FILE_MCP_SOURCE_COMMIT",
            "FILE_MCP_BUILD_DATE",
            "FILE_MCP_CONTAINER_DIGEST",
            "CLOUD_DOG_ENV",
        ):
            runtime_env.pop(key, None)
