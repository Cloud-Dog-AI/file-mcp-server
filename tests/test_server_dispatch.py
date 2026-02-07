from __future__ import annotations

from file_tools.tools import ToolDefinition, ToolMeta, ToolRegistry
from file_mcp_server.server import StdioServer


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            meta=ToolMeta(name="echo", description="Echo tool"),
            handler=lambda text: text,
        )
    )
    return registry


def test_tools_list() -> None:
    server = StdioServer(_build_registry())
    response = server.handle_request({"id": 1, "method": "tools/list"})
    assert response["result"][0]["name"] == "echo"


def test_tools_call() -> None:
    server = StdioServer(_build_registry())
    response = server.handle_request(
        {
            "id": 2,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hi"}},
        }
    )
    assert response["result"] == "hi"


def test_unknown_method() -> None:
    server = StdioServer(_build_registry())
    response = server.handle_request({"id": 3, "method": "missing"})
    assert response["error"]["code"] == -32601
