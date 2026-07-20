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

"""W28E-1870-B REST surface tests for /v1/watches* (PS-102 §5.5).

Drives the real file-mcp ASGI middleware via TestClient with flat-role cookie
auth (the same harness the estate uses), covering CST-API-* (lifecycle + batch
retrieval), CSTREAM-002 (nonblocking pull-batch), CSTREAM-009 (anon/read-only
RBAC), and CST-REC-* (recover).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from file_mcp_server import server_runtime as R
from file_mcp_server.server_runtime import HealthCheckMiddleware
from tests.env_runtime import runtime_env

pytestmark = [pytest.mark.UT, pytest.mark.api]

def _admin() -> tuple[str, str]:
    # W28A-SEC-R17: credentials come from the environment (the same config the
    # server resolves) — no credential literals in the test.
    return (
        runtime_env.get("CLOUD_DOG_WEB_LOGIN_USERNAME", "admin") or "admin",
        runtime_env.get("CLOUD_DOG_WEB_LOGIN_PASSWORD", ""),
    )


def _ro() -> tuple[str, str]:
    # read-only falls back to the resolved admin password when its own override
    # is unset — mirrors the server's flat-role resolution (W28A-SEC-R17).
    admin_pw = runtime_env.get("CLOUD_DOG_WEB_LOGIN_PASSWORD", "")
    return (
        runtime_env.get("CLOUD_DOG_WEB_LOGIN_READ_ONLY_USERNAME", "read-only") or "read-only",
        runtime_env.get("CLOUD_DOG_WEB_LOGIN_READ_ONLY_PASSWORD") or admin_pw,
    )


async def _inner(scope, receive, send) -> None:  # pragma: no cover - fallthrough sink
    await send({"type": "http.response.start", "status": 404,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": b'{"detail":"not found"}'})


@pytest.fixture()
def client() -> TestClient:
    runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
    R.set_shared_watch_service(None)  # isolate watches per test
    mw = HealthCheckMiddleware(
        _inner, health_path="/health", profile_name="default", transport="streamable-http"
    )
    return TestClient(mw, raise_server_exceptions=False)


def _login(client: TestClient, creds) -> dict:
    resp = client.post("/auth/login", json={"username": creds[0], "password": creds[1]})
    assert resp.status_code == 200, resp.text[:200]
    return {k: v for k, v in resp.cookies.items()}


@pytest.mark.UT
@pytest.mark.api
@pytest.mark.req("CSTREAM-009")
def test_anonymous_watch_access_is_rejected(client: TestClient):
    # anon create + list are gated by the route-guard chokepoint (401/403)
    assert client.post("/v1/watches", json={}).status_code in (401, 403)
    assert client.get("/v1/watches").status_code in (401, 403)


@pytest.mark.req("CST-API-001")
def test_admin_ui_token_supports_watch_lifecycle_across_web_to_api_boundary():
    R.set_shared_watch_service(None)
    middleware = HealthCheckMiddleware(
        _inner, health_path="/health", profile_name="default", transport="streamable-http"
    )
    middleware.admin_ui_token = "internal-admin-token"
    client = TestClient(middleware, raise_server_exceptions=False)
    headers = {"x-admin-token": "internal-admin-token"}

    create = client.post(
        "/v1/watches",
        json={"profile": "default", "criteria": {"path": "*.txt"}},
        headers=headers,
    )
    assert create.status_code == 201, create.text[:300]
    watch_id = create.json()["watch_id"]

    listing = client.get("/v1/watches", headers=headers)
    assert listing.status_code == 200
    assert any(item["watch_id"] == watch_id for item in listing.json()["watches"])

    paused = client.post(f"/v1/watches/{watch_id}/pause", headers=headers)
    assert paused.status_code == 200 and paused.json()["state"] == "paused"
    resumed = client.post(f"/v1/watches/{watch_id}/resume", headers=headers)
    assert resumed.status_code == 200 and resumed.json()["state"] == "live"
    deleted = client.delete(f"/v1/watches/{watch_id}", headers=headers)
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True


@pytest.mark.req("CST-API-001")
def test_full_watch_lifecycle_over_rest(client: TestClient):
    cookies = _login(client, _admin())
    # create
    create = client.post(
        "/v1/watches",
        json={"profile": "default", "backend": "local",
              "criteria": {"path": "*.md", "action": ["created", "updated", "deleted"]}},
        cookies=cookies,
    )
    assert create.status_code == 201, create.text[:300]
    wid = create.json()["watch_id"]
    assert create.json()["status"]["state"] == "live"

    # list shows it
    listing = client.get("/v1/watches", cookies=cookies)
    assert listing.status_code == 200
    assert any(w["watch_id"] == wid for w in listing.json()["watches"])

    # status
    status = client.get(f"/v1/watches/{wid}/status", cookies=cookies)
    assert status.status_code == 200 and status.json()["state"] == "live"

    # inject a deterministic event (test-mode, no backend mutation) then read it
    tev = client.post(f"/v1/watches/{wid}/test-event",
                      json={"action": "created", "object_ref": "spec.md"}, cookies=cookies)
    assert tev.status_code == 200, tev.text[:200]

    events = client.get(f"/v1/watches/{wid}/events", cookies=cookies)
    assert events.status_code == 200
    body = events.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["object_ref"] == "spec.md"
    cursor = body["next_cursor"]

    # ack advances the cursor
    ack = client.post(f"/v1/watches/{wid}/ack", json={"ack_cursor": cursor}, cookies=cookies)
    assert ack.status_code == 200

    # recover returns a resume cursor (no replay storm)
    rec = client.post(f"/v1/watches/{wid}/recover", json={}, cookies=cookies)
    assert rec.status_code == 200 and rec.json()["resume_cursor"]

    # pause / resume
    assert client.post(f"/v1/watches/{wid}/pause", cookies=cookies).json()["state"] == "paused"
    assert client.post(f"/v1/watches/{wid}/resume", cookies=cookies).json()["state"] == "live"

    # delete
    dele = client.request("DELETE", f"/v1/watches/{wid}", cookies=cookies)
    assert dele.status_code == 200 and dele.json()["deleted"] is True


@pytest.mark.req("CSTREAM-002")
def test_events_pull_batch_is_nonblocking_empty_when_no_events(client: TestClient):
    cookies = _login(client, _admin())
    wid = client.post("/v1/watches", json={"profile": "default", "criteria": {}}, cookies=cookies).json()["watch_id"]
    # a pull-batch with no pending events returns immediately with an empty batch
    events = client.get(f"/v1/watches/{wid}/events?wait_seconds=5", cookies=cookies)
    assert events.status_code == 200
    assert events.json()["events"] == []


@pytest.mark.req("CSTREAM-009")
def test_read_only_role_cannot_create_but_can_read(client: TestClient):
    # admin creates a watch
    admin_cookies = _login(client, _admin())
    wid = client.post("/v1/watches", json={"profile": "default", "criteria": {}}, cookies=admin_cookies).json()["watch_id"]
    # read-only role: create is denied (403), list is allowed (200)
    ro_cookies = _login(client, _ro())
    denied = client.post("/v1/watches", json={"profile": "default"}, cookies=ro_cookies)
    assert denied.status_code == 403, denied.text[:200]
    allowed = client.get("/v1/watches", cookies=ro_cookies)
    assert allowed.status_code == 200
    assert any(w["watch_id"] == wid for w in allowed.json()["watches"])


@pytest.mark.req("CSTREAM-005")
def test_ack_requires_ack_cursor(client: TestClient):
    cookies = _login(client, _admin())
    wid = client.post("/v1/watches", json={"profile": "default", "criteria": {}}, cookies=cookies).json()["watch_id"]
    resp = client.post(f"/v1/watches/{wid}/ack", json={}, cookies=cookies)
    assert resp.status_code == 422


@pytest.mark.req("CST-API-001")
def test_unknown_watch_id_returns_404(client: TestClient):
    cookies = _login(client, _admin())
    resp = client.get("/v1/watches/does-not-exist/status", cookies=cookies)
    assert resp.status_code == 404
