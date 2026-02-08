from __future__ import annotations

import asyncio
import json

from tests.config_helpers import build_profile
from file_tools.config.models import HttpServerConfig
from file_mcp_server.server import (
    HealthCheckMiddleware,
    build_tool_registry,
    resolve_http_settings,
)


def _profile(tmp_path):
    defaults_yaml = """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
      allow_globs:
        - "**/*"
      deny_globs: []
      allowed_exts: []
      read_only_exts: []
    validation:
      default_mode: "warn"
      per_type: {}
    limits:
      search_max_results: 5
      search_max_file_mb: 1
      conversion_timeout_s: 10
""".lstrip()
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": "secret",
        "FILE_MCP_API_KEY_SECONDARY": "",
        "FILE_MCP_ROOT": str(tmp_path),
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )


def test_resolve_http_settings_with_base_path() -> None:
    config = HttpServerConfig(
        transport="streamable-http",
        host="0.0.0.0",
        port="8123",
        base_path="/api/v1",
        mcp_path="/mcp",
        health_path="/healthz",
        events_path="/events",
        stateless_http="true",
    )
    settings = resolve_http_settings(config)
    assert settings.host == "0.0.0.0"
    assert settings.port == 8123
    assert settings.mcp_path == "/api/v1/mcp"
    assert settings.health_path == "/api/v1/healthz"
    assert settings.events_path == "/api/v1/events"
    assert settings.stateless_http is True


def test_build_tool_registry_wires_real_handlers(tmp_path) -> None:
    profile = _profile(tmp_path)
    registry = build_tool_registry(profile)
    write_handler = registry.get("write_file").handler
    read_handler = registry.get("read_file").handler

    target = tmp_path / "sample.txt"
    write_result = write_handler(str(target), "hello")
    assert write_result["ok"] is True
    assert read_handler(str(target)) == "hello"


def test_health_middleware_returns_ok() -> None:
    sent = []

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/health"}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    status = sent[0]["status"]
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert status == 200
    assert body["status"] == "ok"
