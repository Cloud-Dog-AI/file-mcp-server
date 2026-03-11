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
