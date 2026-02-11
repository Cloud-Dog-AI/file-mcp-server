# API Documentation

## Overview
`file-mcp-server` exposes MCP tools over FastMCP HTTP transports.

Default endpoint paths:
- `GET /` (status summary page for browser; JSON when `Accept: application/json`)
- `GET /health`
- `POST /mcp`
- `GET /admin/google-drive` (when admin UI is enabled)
- `POST /admin/google-drive/start` (when admin UI is enabled)
- `GET /admin/google-drive/callback` (when admin UI is enabled)
- `POST /admin/reload` (when admin UI is enabled)

Configured transport modes:
- `streamable-http` (default): streamable MCP on `/mcp`
- `http`: non-streaming MCP HTTP mode on `/mcp`
- `sse`: SSE MCP mode on `/events`

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

Profile routing:
- default profile is server-configured
- request override via query parameter `profile=<name>`
- request override via header `X-File-MCP-Profile: <name>`
- selected profile controls auth key set, scope rules, and type restrictions

## Core Tool Groups
- Filesystem: `read_file`, `write_file`, `copy_file`, `move_file`, `delete_file`, `list_dir`
- Search: `search_paths`, `search_content`
- Diff/Base64: `diff_text`, `diff_files`, `b64_encode`, `b64_decode`, `b64_encode_file`, `b64_decode_to_file`
- Structured edit: `json_*`, `yaml_*`, `xml_set_file`, `html_set_file`, `markdown_set_section_file`, `markdown_set_frontmatter_file`
- Sed-like: `sed_edit_file` (single op or transaction)
- Validation: `validate_text`, `validate_file`
- Conversion: `convert_file`
- Optional compare UI bridge: `meld_files`
- Runtime backend status: `backend_status`

## Dry-Run Support
Mutating tools that can compute outcomes without writes expose `dry_run=true` behavior and return `dry_run` in payload. Audit entries are still emitted for attempts.

## Validation & Error Shape
Validation behavior is policy-driven (`strict`, `warn`, `ignore` per type/default mode). Tool failures return MCP tool errors with human-readable message and stable internal error handling paths.

## Health Endpoint
`GET /health` returns service status payload without secrets, including transport/profile indicators.

## Admin/OAuth Endpoints

Admin endpoints are available only when `FILE_MCP_ADMIN_UI_ENABLED=true`.
If `FILE_MCP_ADMIN_UI_TOKEN` is set, requests must include either:
- query `?token=<value>`; or
- header `X-Admin-Token: <value>`.

Endpoints:
- `GET /admin/google-drive`: setup form for Google Drive profile binding.
- `POST /admin/google-drive/start`: validates form input and redirects (302) to Google OAuth.
- `GET /admin/google-drive/callback`: exchanges authorization code, validates folder, updates config.
- `POST /admin/reload`: hot-reloads config/profile bindings in-process.

## OpenAPI
Machine-readable HTTP surface documentation is in `openapi.json`.
