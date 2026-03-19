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

"""
file-mcp-server — file_tools/tools/registry.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for tools registry.py.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from .definitions import ToolDefinition


class ToolRegistry:
    def __init__(self) -> None:
        """Initialise the instance state."""
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        """Execute register."""
        if definition.meta.name in self._tools:
            raise KeyError(f"Tool already registered: {definition.meta.name}")
        self._tools[definition.meta.name] = definition

    def list_tools(self) -> List[ToolDefinition]:
        """List tools."""
        return list(self._tools.values())

    def get(self, name: str) -> ToolDefinition:
        """Execute get."""
        return self._tools[name]


def build_registry(definitions: Iterable[ToolDefinition]) -> ToolRegistry:
    """Build registry."""
    registry = ToolRegistry()
    for definition in definitions:
        registry.register(definition)
    return registry
