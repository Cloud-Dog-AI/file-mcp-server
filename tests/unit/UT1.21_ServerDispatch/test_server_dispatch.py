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

from __future__ import annotations

from file_tools.tools import ToolDefinition, ToolMeta, ToolRegistry
from file_mcp_server.server import StdioServer
import pytest


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            meta=ToolMeta(name="echo", description="Echo tool"),
            handler=lambda text: text,
        )
    )
    return registry
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_tools_list() -> None:
    server = StdioServer(_build_registry())
    response = server.handle_request({"id": 1, "method": "tools/list"})
    assert response["result"][0]["name"] == "echo"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_unknown_method() -> None:
    server = StdioServer(_build_registry())
    response = server.handle_request({"id": 3, "method": "missing"})
    assert response["error"]["code"] == -32601
