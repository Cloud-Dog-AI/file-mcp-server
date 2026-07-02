# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from __future__ import annotations

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

import time

import pytest
from fastapi.testclient import TestClient

from file_mcp_server.auth import MultiProfileApiKeyTokenVerifier
from file_mcp_server.mcp_api_kit_layer import build_mcp_fastapi_application
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
