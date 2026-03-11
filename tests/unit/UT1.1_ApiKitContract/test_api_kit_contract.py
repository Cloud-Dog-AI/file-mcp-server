from __future__ import annotations

from tests.env_runtime import runtime_env

import asyncio
import json

from file_mcp_server.server import HealthCheckMiddleware


async def _invoke_middleware(
    middleware, *, method: str, path: str, query: bytes = b"", headers=None
):
    sent: list[dict] = []

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query,
        "headers": headers or [],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)
    return sent


def _middleware() -> HealthCheckMiddleware:
    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )


def test_health_middleware_exposes_ready_and_live() -> None:
    middleware = _middleware()

    ready = asyncio.run(_invoke_middleware(middleware, method="GET", path="/ready"))
    ready_body = json.loads(ready[1]["body"].decode("utf-8"))
    assert ready[0]["status"] == 200
    assert ready_body["status"] in {"ok", "degraded"}
    assert "checks" in ready_body

    live = asyncio.run(_invoke_middleware(middleware, method="GET", path="/live"))
    live_body = json.loads(live[1]["body"].decode("utf-8"))
    assert live[0]["status"] == 200
    assert live_body["status"] == "ok"
    assert "version" in live_body


def test_admin_query_token_is_rejected_with_error_envelope() -> None:
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = "expected-token"

    try:
        middleware = _middleware()
        # Query-string token is intentionally unsupported; header-only auth is required.
        sent = asyncio.run(
            _invoke_middleware(
                middleware,
                method="POST",
                path="/admin/reload",
                query=b"token=expected-token",
            )
        )
        assert sent[0]["status"] == 401
        body = json.loads(sent[1]["body"].decode("utf-8"))
        assert body["ok"] is False
        assert isinstance(body.get("errors"), list) and body["errors"]
        assert body["errors"][0]["code"] == "UNAUTHENTICATED"
        assert "message" in body["errors"][0]
        assert body.get("meta", {}).get("correlation_id")
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token
