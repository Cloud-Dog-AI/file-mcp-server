"""Tool registry tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for tool registry behavior and schema metadata.
Requirements: FR1.1
Tasks: T14
Architecture: 5. Tool Interface, 11. Extensibility
Tests: UT1.17
Recent Change History:
- 2026-02-05: Add header and schema metadata coverage.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from file_tools.tools import (
    ToolDefinition,
    ToolMeta,
    ToolRegistry,
    ToolSchema,
    build_registry,
)


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    text: str


def test_registry_register_and_get() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        meta=ToolMeta(name="echo", description="Echo tool"),
        schema_def=ToolSchema(input_model=EchoInput, output_model=EchoOutput),
        handler=lambda text: text,
    )
    registry.register(definition)

    assert registry.get("echo").meta.name == "echo"


def test_registry_duplicate_registration() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        meta=ToolMeta(name="echo", description="Echo tool"),
        schema_def=ToolSchema(input_model=EchoInput, output_model=EchoOutput),
        handler=lambda text: text,
    )
    registry.register(definition)
    with pytest.raises(KeyError):
        registry.register(definition)


def test_build_registry() -> None:
    definition = ToolDefinition(
        meta=ToolMeta(name="echo", description="Echo tool"),
        schema_def=ToolSchema(input_model=EchoInput, output_model=EchoOutput),
        handler=lambda text: text,
    )
    registry = build_registry([definition])
    tool = registry.get("echo")
    assert tool.schema_def.input_model is EchoInput
    assert tool.schema_def.output_model is EchoOutput


def test_registry_list_deterministic() -> None:
    registry = ToolRegistry()
    first = ToolDefinition(
        meta=ToolMeta(name="alpha", description="Alpha"),
        handler=lambda: "alpha",
    )
    second = ToolDefinition(
        meta=ToolMeta(name="beta", description="Beta"),
        handler=lambda: "beta",
    )
    registry.register(first)
    registry.register(second)

    names = [tool.meta.name for tool in registry.list_tools()]
    assert names == ["alpha", "beta"]
