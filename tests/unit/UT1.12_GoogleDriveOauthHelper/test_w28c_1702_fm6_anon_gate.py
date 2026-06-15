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

"""file-mcp-server — UT1.12 FM6: /admin/google-drive* anonymous-gate.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: W28C-1702 (FM6/1601-A) — the four google-drive admin surfaces must
deny anonymous callers (401 JSON) and admit an admin-cookie session, closing the
OAuth client_id leak. Tests: UT1.12
"""


from __future__ import annotations
import pytest

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

import asyncio
import time

from file_mcp_server.server import HealthCheckMiddleware


async def _noop_app(scope, receive, send) -> None:  # pragma: no cover
    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})


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


GDRIVE_PATHS = [
    ("GET", "/admin/google-drive"),
    ("POST", "/admin/google-drive/start"),
    ("GET", "/admin/google-drive/callback"),
    ("GET", "/google-drive-settings"),
]


def _mw():
    # admin_ui_enabled=true with NO admin_ui_token is the exact legacy_open_access
    # condition that previously let anonymous callers through.
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


def test_fm6_anonymous_denied_on_all_four_gdrive_surfaces() -> None:
    mw = _mw()
    for method, path in GDRIVE_PATHS:
        sent = _run(mw, method=method, path=path)  # no auth headers, no Accept
        status = sent[0]["status"]
        assert status == 401, f"anon {method} {path} -> {status}, expected 401"
        # No client_id must appear in any anonymous response body.
        body = b"".join(
            m.get("body", b"") for m in sent if m.get("type") == "http.response.body"
        )
        assert b"client_id" not in body
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_fm6_admin_cookie_session_admitted() -> None:
    mw = _mw()
    mw._sessions["w28c1702-sess"] = {
        "user": "admin",
        "user_id": "1",
        "role": "admin",
        "_created": time.time(),
    }
    cookie = [(b"cookie", b"file_web_session=w28c1702-sess")]
    for method, path in GDRIVE_PATHS:
        sent = _run(mw, method=method, path=path, headers=cookie)
        status = sent[0]["status"]
        # The admin session must clear the gate (no 401/403 denial).
        assert status not in (401, 403), f"admin {method} {path} -> {status}"
