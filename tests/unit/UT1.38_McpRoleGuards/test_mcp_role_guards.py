# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from __future__ import annotations

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from mcp.server.auth.middleware.auth_context import get_access_token

from file_mcp_server.auth import MultiProfileApiKeyTokenVerifier
from file_mcp_server.mcp_api_kit_layer import build_mcp_fastapi_application
from file_mcp_server.server_runtime import HttpRuntimeSettings, build_mcp_server
from file_tools.config.models import ProfileConfig, ServerConfig
from file_tools.tools import ToolDefinition, ToolMeta, ToolRegistry


def _client() -> TestClient:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            meta=ToolMeta(name="list_dir", description="List directory"),
            handler=lambda path=".", recursive=False: {"entries": ["/workspace"]},
        )
    )
    registry.register(
        ToolDefinition(
            meta=ToolMeta(name="write_file", description="Write file", mutating=True),
            handler=lambda path=".", content="": {"ok": True},
        )
    )
    registry.register(
        ToolDefinition(
            meta=ToolMeta(name="whoami", description="Current principal"),
            handler=lambda: {
                "client_id": getattr(get_access_token(), "client_id", None),
                "claims": getattr(get_access_token(), "claims", {}),
            },
        )
    )
    registry.register(
        ToolDefinition(
            meta=ToolMeta(
                name="admin_create_user",
                description="Create admin user",
                mutating=True,
            ),
            handler=lambda username="x": {"ok": True},
        )
    )

    def registry_provider() -> ToolRegistry:
        return registry

    def profile_tool_factory(name: str):
        return registry.get(name).handler

    sessions = {
        "read-only-session": {
            "user_id": "u-read-only",
            "user": "read-only",
            "role": "read-only",
            "_created": time.time(),
        }
    }
    verifier = MultiProfileApiKeyTokenVerifier(
        {"default": (["profile-api-key"], "Authorization", "Bearer")},
        default_profile="default",
    )
    app = build_mcp_fastapi_application(
        registry_provider,
        verifier,
        profile_tool_factory=profile_tool_factory,
        web_session_store=sessions,
    )
    return TestClient(app, raise_server_exceptions=False)


def _tools_call(name: str, arguments: dict | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "w28e-1802b-a",
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("CS-010")
def test_non_admin_api_key_gets_http_403_for_admin_mcp_tool() -> None:
    client = _client()

    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer profile-api-key"},
        json=_tools_call("admin_create_user", {"username": "denied"}),
    )

    assert response.status_code == 403
    assert "admin:*" in response.text


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("CS-010")
def test_primary_profile_api_key_is_not_promoted_to_admin() -> None:
    previous = runtime_env.get("FILE_MCP_API_KEY_PRIMARY")
    runtime_env["FILE_MCP_API_KEY_PRIMARY"] = "profile-api-key"
    try:
        config = ServerConfig(
            profiles={
                "default": ProfileConfig.model_validate(
                    {
                        "auth": {
                            "api_keys": ["${FILE_MCP_API_KEY_PRIMARY}"],
                            "header_name": "Authorization",
                            "header_scheme": "Bearer",
                        },
                        "storage": {"backend": "local"},
                        "scope": {"roots": ["/workspace"]},
                    }
                )
            }
        )
        server = build_mcp_server(
            "default",
            config,
            HttpRuntimeSettings(
                transport="streamable-http",
                host="127.0.0.1",
                port=8080,
                mcp_path="/mcp",
                health_path="/health",
                events_path="/events",
                stateless_http=True,
            ),
        )
        verifier = server._file_mcp_auth_verifier
        token = asyncio.run(
            verifier.verify_token_for_profile("profile-api-key", "default")
        )
    finally:
        if previous is None:
            runtime_env.pop("FILE_MCP_API_KEY_PRIMARY", None)
        else:
            runtime_env["FILE_MCP_API_KEY_PRIMARY"] = previous

    assert token is not None
    assert "*" not in set(token.scopes)
    assert "admin:*" not in set(token.scopes)
    assert token.claims.get("role") != "admin"
    assert "profile:default" in set(token.scopes)


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("CS-010")
def test_read_only_webmcp_can_read_but_cannot_write() -> None:
    client = _client()
    cookies = {"file_web_session": "read-only-session"}

    read_response = client.post(
        "/webmcp",
        cookies=cookies,
        json=_tools_call("list_dir", {"path": "/workspace"}),
    )
    assert read_response.status_code == 200, read_response.text[:200]
    assert "/workspace" in read_response.text

    write_response = client.post(
        "/webmcp",
        cookies=cookies,
        json=_tools_call("write_file", {"path": "x.txt", "content": "x"}),
    )
    assert write_response.status_code == 403
    assert "file:write" in write_response.text


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-017")
def test_bearer_and_cookie_principals_reach_tool_auth_context() -> None:
    client = _client()

    bearer_response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer profile-api-key"},
        json=_tools_call("whoami"),
    )
    assert bearer_response.status_code == 200
    assert '"client_id": null' not in bearer_response.text

    cookie_response = client.post(
        "/webmcp",
        cookies={"file_web_session": "read-only-session"},
        json=_tools_call("whoami"),
    )
    assert cookie_response.status_code == 200
    assert "u-read-only" in cookie_response.text
