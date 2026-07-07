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

"""file-mcp-server — UT1.41 W28E-1863 fix-wave-b.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Two wave-3-audit defects, REDONE on the known-good bundle after the
  fix-wave-a Accept-header approach regressed (post-login blank render, PDS-007).
  (1) Deep-link SPA fallback via the deployed chat-client BLOCKLIST
      (``is_spa_document_navigation``, commit 2156ef9), wired as the fallback of
      LAST RESORT at the terminal ASGI fallthrough — so it can NEVER shadow an
      explicit API/MCP/A2A/auth/admin-gate/asset handler (which is what made
      fix-wave-a leak the API 401/404 and render a blank shell). An extensionless
      browser document navigation to a non-reserved route (bare ``/admin``,
      ``/admin/<not-enumerated>``, ``/system/preferences``, ``/research``) serves
      the SPA index.html shell; reserved API paths still return their gated JSON.
  (2) WSC-014 build identity: /version and /runtime-config.js expose
      source_commit + build_date + container_digest + environment so the WebUI
      About page can render build provenance (PS-30 UI-R7.3), modelled on
      search-mcp's reference. Kept SEPARABLE from the deep-link change.
Tests: UT1.41
"""

from __future__ import annotations

import asyncio
import json

import pytest

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

from file_mcp_server.server import HealthCheckMiddleware
from file_mcp_server.server_runtime import is_spa_document_navigation


async def _noop_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
    # Emulates the inner ASGI app's raw 404 for any path the middleware does not
    # handle itself. The blocklist fallback must intercept SPA document navigations
    # BEFORE this fires.
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


def _mw():
    # admin_ui_enabled=true with NO admin_ui_token is the exact FM6 legacy-open
    # condition; keeps this suite aligned with the UT1.12 anon-gate contract.
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
    return HealthCheckMiddleware(
        _noop_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )


# ───────────────── Defect 1a: blocklist helper (pure unit) ─────────────────

# Extensionless, non-reserved routes -> SPA document navigations. Bare /admin and
# any /admin/<sub> not in the enumerated allowlist are the concrete deep-link
# regression the fix-wave-a lesson calls out.
SPA_DOC_PATHS = [
    "/admin",
    "/admin/preferences",
    "/admin/some-future-tab",
    "/system/preferences",
    "/research",
    "/catalogue",
    "/dashboard/insights",
]

# Reserved server-side surfaces + static-file requests -> NEVER the SPA shell.
NON_SPA_PATHS = [
    "/api",
    "/api/v1/users",
    "/v1/admin/users",
    "/webmcp",
    "/webmcp/tools",
    "/weba2a/events",
    "/a2a/tasks",
    "/auth/login",
    "/assets/index-abc.js",
    "/files/report",
    "/idam/users",
    "/.well-known/agent.json",
    "/health",
    "/ready",
    "/live",
    "/status",
    "/version",
    "/openapi",
    "/runtime-config.js",
    "/favicon.ico",
    "/foo.js",
    "/sitemap.xml",
    "/",
    "",
]


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-017")
@pytest.mark.parametrize("path", SPA_DOC_PATHS)
def test_blocklist_spa_document_navigations(path: str) -> None:
    assert is_spa_document_navigation(path) is True, path


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-017")
@pytest.mark.parametrize("path", NON_SPA_PATHS)
def test_blocklist_reserved_and_static_paths_excluded(path: str) -> None:
    assert is_spa_document_navigation(path) is False, path


# ───────────────── Defect 1b: dispatch — unauth browser deep-link ─────────────────


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-017")
def test_unauth_browser_deeplink_serves_spa_shell_not_404() -> None:
    """Bare /admin + non-enumerated deep routes -> SPA shell (200 text/html),
    NOT the inner-app 404 JSON. The SPA renders its own login gate for anon."""
    mw = _mw()
    for path in ["/admin", "/admin/some-future-tab", "/system/preferences", "/research"]:
        sent = _run(mw, method="GET", path=path, headers=BROWSER)  # no auth
        status = _status(sent)
        ctype = _content_type(sent)
        assert status == 200, f"unauth browser GET {path} -> {status}, expected 200 SPA"
        assert "text/html" in ctype, f"unauth browser GET {path} ct={ctype!r}"
        assert b"error" not in _body(sent) or b"<" in _body(sent), path


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-017")
def test_head_deeplink_serves_spa_shell() -> None:
    """A HEAD document navigation is also served the SPA shell (no body)."""
    mw = _mw()
    sent = _run(mw, method="HEAD", path="/admin", headers=BROWSER)
    assert _status(sent) == 200
    assert "text/html" in _content_type(sent)


# ───────────────── Defect 1c: reserved API paths NOT shadowed (anti-regression) ─────────────────


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")
def test_unauth_api_paths_not_shadowed_by_spa_fallback() -> None:
    """The blocklist fallback must NOT swallow reserved API surfaces: an
    unauthenticated API GET keeps its gated (non-200-HTML) response — this is the
    anti-shadow property fix-wave-a's Accept approach lacked (PDS-007 blank)."""
    mw = _mw()
    for path in ["/api/v1/files", "/webmcp/tools", "/v1/admin/users"]:
        sent = _run(mw, method="GET", path=path, headers=API)  # no auth, JSON accept
        ctype = _content_type(sent)
        # Never the SPA shell for a reserved API surface.
        assert "text/html" not in ctype, f"API {path} was shadowed by SPA: ct={ctype!r}"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")
def test_fm6_google_drive_settings_browser_gate_preserved() -> None:
    """FM6 OAuth-leak contract: an unauthenticated /google-drive-settings request
    is admin-gated (browser -> 302 login redirect, API -> 401 JSON) and NEVER
    leaks the OAuth client_id — the enumerated gate above the fallback still owns
    this route, the blocklist never sees it."""
    mw = _mw()
    # API client (JSON accept): 401 JSON, no client_id.
    sent_api = _run(mw, method="GET", path="/google-drive-settings", headers=API)
    assert _status(sent_api) == 401
    assert b"client_id" not in _body(sent_api)
    # Browser (text/html): admin gate redirects to the SPA login route (302),
    # which itself serves the SPA — either way NOT a raw 404 and no client_id.
    sent_browser = _run(mw, method="GET", path="/google-drive-settings", headers=BROWSER)
    assert _status(sent_browser) in (200, 302, 303, 307, 308)
    assert b"client_id" not in _body(sent_browser)


# ───────────────── Defect 2: WSC-014 build identity ─────────────────


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-010.3")
def test_version_endpoint_exposes_build_identity() -> None:
    """/version exposes commit/build/deploy identity (WSC-014)."""
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
        # legacy field the DashboardPage VersionInfo already reads
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
    """/runtime-config.js exposes APP_COMMIT / APP_BUILD_DATE / etc. (WSC-014)."""
    runtime_env["FILE_MCP_SOURCE_COMMIT"] = "abc1234def5678901234567890abcdef12345678"
    runtime_env["FILE_MCP_BUILD_DATE"] = "2026-07-07T12:00:00Z"
    runtime_env["FILE_MCP_CONTAINER_DIGEST"] = "sha256:deadbeefcafebabe"
    runtime_env["CLOUD_DOG_ENV"] = "preprod"
    try:
        mw = _mw()
        sent = _run(mw, method="GET", path="/runtime-config.js")
        assert _status(sent) == 200
        assert "javascript" in _content_type(sent)
        body = _body(sent).decode("utf-8")
        assert '"APP_COMMIT": "abc1234def5678901234567890abcdef12345678"' in body
        assert '"APP_BUILD_DATE": "2026-07-07T12:00:00Z"' in body
        assert '"APP_CONTAINER_DIGEST": "sha256:deadbeefcafebabe"' in body
        assert '"APP_ENV": "preprod"' in body
    finally:
        for key in (
            "FILE_MCP_SOURCE_COMMIT",
            "FILE_MCP_BUILD_DATE",
            "FILE_MCP_CONTAINER_DIGEST",
            "CLOUD_DOG_ENV",
        ):
            runtime_env.pop(key, None)
