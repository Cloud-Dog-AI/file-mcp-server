# API Documentation

## Overview
`file-mcp-server` exposes MCP tools over FastMCP HTTP transport.

Default endpoints:
- `GET /health`
- `POST /mcp`

Optional SSE transport also exposes an events path (default `/events`) when configured.

## Authentication
All tool calls require API key authentication.

Default auth contract:
- Header: `Authorization`
- Scheme: `Bearer`
- Example: `Authorization: Bearer <api-key>`

Header name/scheme are profile-configurable.

## Transport Contract
`/mcp` uses JSON-RPC style MCP tool invocation via FastMCP.
Typical workflow:
1. Discover tools.
2. Call a tool with JSON arguments.
3. Receive structured tool result or structured tool error.

## Core Tool Groups
- Filesystem: `read_file`, `write_file`, `copy_file`, `move_file`, `delete_file`, `list_dir`
- Search: `search_paths`, `search_content`
- Diff/Base64: `diff_text`, `diff_files`, `b64_encode`, `b64_decode`, `b64_encode_file`, `b64_decode_to_file`
- Structured edit: `json_*`, `yaml_*`, `xml_set_file`, `html_set_file`, `markdown_set_section_file`, `markdown_set_frontmatter_file`
- Sed-like: `sed_edit_file` (single op or transaction)
- Validation: `validate_text`, `validate_file`
- Conversion: `convert_file`
- Optional compare UI bridge: `meld_files`

## Dry-Run Support
Mutating tools that can compute outcomes without writes expose `dry_run=true` behavior and return `dry_run` in payload. Audit entries are still emitted for attempts.

## Validation & Error Shape
Validation behavior is policy-driven (`strict`, `warn`, `ignore` per type/default mode). Tool failures return MCP tool errors with human-readable message and stable internal error handling paths.

## Health Endpoint
`GET /health` returns service status payload without secrets, including transport/profile indicators.

## OpenAPI
Machine-readable HTTP surface documentation is in `openapi.json`.
