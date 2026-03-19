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
file-mcp-server — file_tools/tools/definitions.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for tools definitions.py.
"""

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
