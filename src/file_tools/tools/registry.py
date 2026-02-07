"""Tool registry scaffolding."""

from __future__ import annotations

from typing import Dict, Iterable, List

from .definitions import ToolDefinition


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.meta.name in self._tools:
            raise KeyError(f"Tool already registered: {definition.meta.name}")
        self._tools[definition.meta.name] = definition

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]


def build_registry(definitions: Iterable[ToolDefinition]) -> ToolRegistry:
    registry = ToolRegistry()
    for definition in definitions:
        registry.register(definition)
    return registry
