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

"""file-mcp-server — Pydantic input schemas for MCP tool calls.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Provides explicit inputSchema definitions (W28A-240) so LLM clients
generate correct parameter names instead of guessing from descriptions.
Also provides alias normalization for common LLM-generated alternatives.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace root")
    encoding: str = Field("utf-8", description="Text encoding")
    start_line: Optional[int] = Field(None, description="Start line number (1-based)")
    end_line: Optional[int] = Field(None, description="End line number (1-based)")


class WriteFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace root")
    content: str = Field(..., description="Text content to write")
    encoding: str = Field("utf-8", description="Text encoding")
    overwrite: bool = Field(True, description="Overwrite existing file")
    dry_run: bool = Field(False, description="Preview without writing")


class CreateDirInput(BaseModel):
    path: str = Field(..., description="Directory path relative to workspace root")
    parents: bool = Field(True, description="Create parent directories")
    exist_ok: bool = Field(True, description="No error if directory exists")
    dry_run: bool = Field(False, description="Preview without creating")


class ListDirInput(BaseModel):
    path: str = Field(".", description="Directory path relative to workspace root")
    recursive: bool = Field(False, description="List recursively")


class ConvertFileInput(BaseModel):
    path: str = Field(..., description="Source file path")
    target_format: str = Field(..., description="Target format (e.g. html, pdf, txt)")
    output_path: Optional[str] = Field(None, description="Output file path")


class ValidateFileInput(BaseModel):
    path: str = Field(..., description="File path to validate")
    content_type: Optional[str] = Field(None, description="Expected content type (yaml, json, etc.)")
    encoding: str = Field("utf-8", description="Text encoding")


class SearchContentInput(BaseModel):
    query: str = Field(..., description="Search text or pattern")
    glob: Optional[str] = Field(None, description="Glob pattern to filter files (e.g. '*.md', 'docs/**')")
    regex: bool = Field(False, description="Treat query as regex")
    max_results: Optional[int] = Field(None, description="Maximum results to return")


class SedEditFileInput(BaseModel):
    path: str = Field(..., description="File path to edit")
    op: Optional[str] = Field(None, description="Operation: replace, delete, insert")
    pattern: Optional[str] = Field(None, description="Search pattern (regex)")
    repl: Optional[str] = Field(None, description="Replacement text")
    count: int = Field(0, description="Max replacements (0=all)")
    dry_run: bool = Field(False, description="Preview without editing")


class ReplaceRegexInput(BaseModel):
    path: str = Field(..., description="File path to edit")
    pattern: str = Field(..., description="Regex pattern to find")
    replacement: str = Field(..., description="Replacement text")
    count: int = Field(0, description="Max replacements (0=all)")
    dry_run: bool = Field(False, description="Preview without editing")


# Common LLM-generated aliases → canonical parameter names
PARAM_ALIASES: dict[str, str] = {
    "file_path": "path",
    "filepath": "path",
    "file_name": "path",
    "filename": "path",
    "name": "path",
    "directory": "path",
    "dir": "path",
    "folder": "path",
    "data": "content",
    "text": "content",
    "body": "content",
    "file_content": "content",
    "search_query": "query",
    "search_term": "query",
    "term": "query",
    "format": "target_format",
    "output_format": "target_format",
    "to_format": "target_format",
    "search": "query",
    "replace": "repl",
    "replacement_text": "repl",
    "replace_with": "repl",
    "type": "content_type",
    "file_type": "content_type",
}


def normalize_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Normalize LLM-generated parameter aliases to canonical names.

    Only remaps known safe aliases. Unknown parameters are passed through.
    """
    result: dict[str, Any] = {}
    for key, value in args.items():
        canonical = PARAM_ALIASES.get(key, key)
        if canonical not in result:
            result[canonical] = value
    return result


def normalize_and_filter_tool_args(
    args: dict[str, Any],
    handler: Any,
) -> dict[str, Any]:
    """Normalize args then filter to only those accepted by *handler*.

    This prevents ``normalize_tool_args`` from remapping a caller-supplied
    parameter (e.g. ``text``) to a canonical name (e.g. ``content``) that
    the handler's signature does not declare, which causes a TypeError.

    When normalization produces no matching parameters the original
    (pre-normalization) keys are tried as a fallback so that handlers
    whose parameter names happen to collide with alias *sources* still
    receive the values they expect.
    """
    import inspect

    normalized = normalize_tool_args(args)

    sig = inspect.signature(handler)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return normalized

    accepted = {k: v for k, v in normalized.items() if k in sig.parameters}
    if not accepted and args:
        accepted = {k: v for k, v in args.items() if k in sig.parameters}
    return accepted
