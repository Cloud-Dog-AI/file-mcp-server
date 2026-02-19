"""Tool model definitions scaffolding."""

from __future__ import annotations

from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class ToolMeta(BaseModel):
    name: str
    description: str
    mutating: bool = False
    requires_validation: bool = False
    supports_dry_run: bool = False


class ToolSchema(BaseModel):
    input_model: Optional[type[BaseModel]] = None
    output_model: Optional[type[BaseModel]] = None


class ToolDefinition(BaseModel):
    meta: ToolMeta
    schema_def: ToolSchema = Field(default_factory=ToolSchema)
    handler: Callable[..., Any]
