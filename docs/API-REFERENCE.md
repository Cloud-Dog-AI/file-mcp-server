# File MCP Server API Reference

## 1. REST API

Authentication: API key for protected MCP/A2A/admin operations. Health endpoint is read-only status.

| Method | Path | Purpose | Auth | Request | Response | Errors |
|---|---|---|---|---|---|---|
| `GET` | `/` | Root Status Summary | Not required | None | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `GET` | `/admin/google-drive` | Google Drive Setup Page | Required (Bearer API key) | None | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `GET` | `/admin/google-drive/callback` | Google OAuth Callback | Required (Bearer API key) | None | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `POST` | `/admin/google-drive/start` | Start Google OAuth | Required (Bearer API key) | JSON body | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `POST` | `/admin/reload` | Reload Active Configuration | Required (Bearer API key) | JSON body | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `GET` | `/health` | Health Check | Not required | None | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |
| `GET` | `/runtime-config.js` | UI runtime bootstrap config (`window.__RUNTIME_CONFIG__`) | Not required | None | JavaScript payload | `400`, `404`, `500` |
| `GET` | `/ui`, `/ui/*` | File MCP SPA shell (`ui/dist/index.html` fallback) | Not required | None | HTML payload | `404`, `503` |
| `GET` | `/assets/*`, `/ui/assets/*` | Static SPA assets from `ui/dist/assets` | Not required | None | Static file payload | `404` |
| `GET` | `/api/v1/jobs` | List managed jobs for selected profile | Required (Bearer API key) | Query: `limit`, `status`, `session_id`, `job_type` | JSON payload | `400`, `401`, `403`, `404`, `405`, `500`, `503` |
| `GET` | `/api/v1/jobs/queue/status` | Return queue status counters | Required (Bearer API key) | None | JSON payload | `400`, `401`, `403`, `404`, `405`, `500`, `503` |
| `GET` | `/api/v1/jobs/{job_id}` | Read one managed job | Required (Bearer API key) | None | JSON payload | `400`, `401`, `403`, `404`, `405`, `500`, `503` |
| `POST` | `/mcp` | MCP Tool Endpoint | Required (Bearer API key) | JSON body | JSON payload | `400`, `401`, `403`, `404`, `500` (contract-dependent) |

### OpenAPI

- Runtime: `/openapi.json`
- Repository file: [`openapi.json`](../openapi.json)

## 2. MCP Tools

MCP endpoint: `POST /mcp`

Canonical operations:
- `tools/list` -> returns all available tools and metadata
- `tools/call` -> executes a tool with JSON arguments

Example request (tool discovery):
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/list",
  "params": {}
}
```

Example request (tool call):
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {"path": "README.md"}
  }
}
```

| Tool | Description | Mutating | Parameters | Return Schema |
|---|---|---|---|---|
| `b64_decode` | Decode base64 to text | no | `data, encoding='utf-8', urlsafe=False` | JSON object; schema depends on tool |
| `b64_decode_to_file` | Decode base64 to file (managed job when enabled) | yes | `path, data, urlsafe=False, overwrite=True, dry_run=False` | JSON object; includes `job_id` when jobs are enabled |
| `b64_encode` | Encode text as base64 | no | `text, encoding='utf-8', urlsafe=False` | JSON object; schema depends on tool |
| `b64_encode_file` | Encode file contents as base64 | no | `path, urlsafe=False` | JSON object; schema depends on tool |
| `backend_status` | Return endpoint health states for configured storage backends | no | `-` | JSON object; schema depends on tool |
| `chmod_path` | Change file or directory mode | yes | `path, mode, recursive=False, dry_run=False` | JSON object; schema depends on tool |
| `convert_file` | Convert file with limits and warning-based optional backend handling (managed job when enabled) | no | `path, target_format, output_path=None, max_input_mb=None, timeout_s=None, simulate_delay_s=None, backend=None` | JSON object; includes `job_id` when jobs are enabled |
| `copy_file` | Copy a file | yes | `src, dst, overwrite=False, dry_run=False` | JSON object; schema depends on tool |
| `create_dir` | Create a directory | yes | `path, parents=True, exist_ok=True, dry_run=False` | JSON object; schema depends on tool |
| `delete_file` | Delete a file | yes | `path, missing_ok=False, dry_run=False` | JSON object; schema depends on tool |
| `diff_files` | Generate unified diff for files | no | `path_a, path_b, encoding='utf-8', context=3` | JSON object; schema depends on tool |
| `diff_text` | Generate unified diff for text | no | `before, after, context=3` | JSON object; schema depends on tool |
| `html_set_file` | Set HTML value in file with validation/audit/snapshot | yes | `path, selector, value, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `json_copy` | Copy JSON value by path | yes | `text, from_path, to_path` | JSON object; schema depends on tool |
| `json_copy_file` | Copy JSON value in file with validation/audit/snapshot | yes | `path, from_path, to_path, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `json_delete` | Delete JSON value by path | yes | `text, path` | JSON object; schema depends on tool |
| `json_get` | Get JSON value by path | no | `text, path` | JSON object; schema depends on tool |
| `json_get_file` | Get JSON value from file by path | no | `path, json_path, encoding='utf-8'` | JSON object; schema depends on tool |
| `json_merge` | Merge JSON value by path | yes | `text, path, value` | JSON object; schema depends on tool |
| `json_merge_file` | Merge JSON value in file with validation/audit/snapshot | yes | `path, value, json_path='/', encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `json_move` | Move JSON value by path | yes | `text, from_path, to_path` | JSON object; schema depends on tool |
| `json_move_file` | Move JSON value in file with validation/audit/snapshot | yes | `path, from_path, to_path, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `json_set` | Set JSON value by path | yes | `text, path, value` | JSON object; schema depends on tool |
| `json_set_file` | Set JSON value in file with validation/audit/snapshot | yes | `path, json_path, value, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `list_dir` | List directory entries | no | `path, recursive=False` | JSON object; schema depends on tool |
| `markdown_get_section` | Extract markdown section | no | `text, heading` | JSON object; schema depends on tool |
| `markdown_set_frontmatter_file` | Update markdown YAML frontmatter with validation/audit/snapshot | yes | `path, updates, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `markdown_set_section` | Replace markdown section | yes | `text, heading, new_content` | JSON object; schema depends on tool |
| `markdown_set_section_file` | Set markdown section in file with validation/audit/snapshot | yes | `path, heading, new_content, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `meld_files` | Launch meld for file comparison (optional integration) | no | `path_a, path_b` | JSON object; schema depends on tool |
| `move_file` | Move a file or directory | yes | `src, dst, overwrite=False, dry_run=False, tool_name='move_file'` | JSON object; schema depends on tool |
| `move_path` | Move a file or directory | yes | `src, dst, overwrite=False, dry_run=False` | JSON object; schema depends on tool |
| `read_file` | Read a text file | no | `path, encoding='utf-8', start_line=None, end_line=None, start_byte=None, end_byte=None` | JSON object; schema depends on tool |
| `rename_path` | Rename a file or directory | yes | `src, dst, overwrite=False, dry_run=False` | JSON object; schema depends on tool |
| `replace_regex` | Apply regex replacement | yes | `text, pattern, repl, count=0` | JSON object; schema depends on tool |
| `search_content` | Search file contents | no | `query, glob=None, regex=False, max_results=None, encoding='utf-8', max_file_mb=None, max_depth=None, timeout_s=None` | JSON object; schema depends on tool |
| `search_paths` | Search file paths | no | `query, glob=None, regex=False, max_results=None, max_file_mb=None, max_depth=None, timeout_s=None` | JSON object; schema depends on tool |
| `sed_edit_file` | Apply sed-like file edits with audit/snapshot support | yes | `path, op=None, pattern=None, repl=None, count=0, line_no=None, content=None, start=None, end=None, replacement=None, operations=None, dry_run=False, encoding='utf-8'` | JSON object; schema depends on tool |
| `validate_file` | Validate file content by detected or explicit type | no | `path, content_type=None, encoding='utf-8'` | JSON object; schema depends on tool |
| `validate_text` | Validate text content by type | no | `content_type, text` | JSON object; schema depends on tool |
| `write_file` | Write text to a file | yes | `path, content, encoding='utf-8', overwrite=True, dry_run=False` | JSON object; schema depends on tool |
| `xml_set_file` | Set XML value in file with validation/audit/snapshot | yes | `path, xpath, value, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `yaml_copy` | Copy YAML value by path | yes | `text, from_path, to_path` | JSON object; schema depends on tool |
| `yaml_copy_file` | Copy YAML value in file with validation/audit/snapshot | yes | `path, from_path, to_path, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `yaml_delete` | Delete YAML value by path | yes | `text, path` | JSON object; schema depends on tool |
| `yaml_delete_file` | Delete YAML value in file with validation/audit/snapshot | yes | `path, yaml_path, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `yaml_get` | Get YAML value by path | no | `text, path` | JSON object; schema depends on tool |
| `yaml_get_file` | Get YAML value from file by path | no | `path, yaml_path, encoding='utf-8'` | JSON object; schema depends on tool |
| `yaml_merge` | Merge YAML value by path | yes | `text, path, value` | JSON object; schema depends on tool |
| `yaml_merge_file` | Merge YAML mapping into file with validation/audit/snapshot | yes | `path, value, yaml_path='/', encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `yaml_move` | Move YAML value by path | yes | `text, from_path, to_path` | JSON object; schema depends on tool |
| `yaml_move_file` | Move YAML value in file with validation/audit/snapshot | yes | `path, from_path, to_path, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |
| `yaml_set` | Set YAML value by path | yes | `text, path, value` | JSON object; schema depends on tool |
| `yaml_set_file` | Set YAML value in file with validation/audit/snapshot | yes | `path, yaml_path, value, encoding='utf-8', dry_run=False` | JSON object; schema depends on tool |

## 3. A2A Endpoint

| Method | Path | Purpose | Auth | Response |
|---|---|---|---|---|
| `GET` | `/a2a/health` | A2A health contract in local runtime test mode | Required (`Authorisation: Bearer <API key>`) | `200` with valid key, `401` otherwise |

## 4. Error Contract

- MCP tool errors are returned as structured JSON-RPC errors.
- REST/admin endpoints use structured JSON error payloads aligned to platform API standards.
- Common failure classes: auth failure, scope validation, backend unavailable, validation failure, timeout.



<!-- W28C-1710a recovery: full content from archive/2026-06-12/API_DOCUMENTATION.md (archived sha256=e7b0eaf30d9c, 234 lines) -->

## Recovered domain content — `archive/2026-06-12/API_DOCUMENTATION.md` (234 lines)

_This section carries forward the full content of the archived predecessor doc verbatim. Topic checklist + SHA256 chain in `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/file-mcp-server/API_DOCUMENTATION.md.topics.tsv`. Archive contents are unchanged (sha256 stable)._

# API Documentation

## Overview
`file-mcp-server` is an MCP-native service. Clients interact primarily through MCP JSON-RPC over streamable-HTTP (or legacy SSE). Administrative and operational HTTP endpoints are also exposed on the same port. There are no traditional REST resource routes.

## Base URLs
- Local development: `http://localhost:8083` (port configurable via `FILE_MCP_HTTP_PORT`)
- Default MCP path: `/mcp` (configurable via `FILE_MCP_HTTP_MCP_PATH`)

## Authentication
- MCP tool calls: API key passed as Bearer token or `X-API-Key` header. Profile-routed; each profile may have its own key set.
- Admin endpoints: `X-Admin-Token` header, cookie-based web session, or API key with admin scope.
- A2A task submission: Authenticated via the same API key verifier.

## Verification Basis
- Source files reviewed: `src/file_mcp_server/server_runtime.py`, `src/file_mcp_server/mcp_api_kit_layer.py`
- MCP tool count: 65 (54 core + 11 admin identity tools when enabled)
- HTTP endpoint count: 20+

## Transport Endpoints

### MCP Transport
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/mcp` | API key/JWT | Primary MCP JSON-RPC endpoint (streamable-HTTP mode). Handles `tools/list`, `tools/call`, and standard MCP lifecycle methods. |
| POST | `/webmcp` | API key/JWT | Alternate MCP path used by the embedded WebUI client. |
| GET | `/mcp/tools` | Optional | Tool catalogue helper; returns registered tool names and descriptions. |
| GET | `/webmcp/tools` | Optional | Same tool catalogue via the WebUI MCP path. |

### Health, Readiness, and Status
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness probe with profile health summary. Path configurable via `FILE_MCP_HTTP_HEALTH_PATH`. |
| GET | `/ready` | None | Readiness check with dependency probes (DB, storage backends). |
| GET | `/live` | None | Simple liveness response with version and service name. |
| GET | `/status` | None | Extended status payload (profiles, server ID, uptime, backend states). |

### A2A (Agent-to-Agent)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/.well-known/agent.json` | None | A2A agent card advertising skills: `file-management`, `file-search`, `gdrive-sync`. |
| POST | `/a2a/tasks` | API key | A2A task submission; dispatches to skill handlers which invoke MCP tools. |
| GET | `/a2a/health` | None | A2A-specific health check. |

### Admin
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/admin/reload` | Admin token | Hot-reload profile and tool registry from config/defaults files. |
| GET | `/admin/google-drive` | Admin auth | Google Drive OAuth setup page (HTML). |
| POST | `/admin/google-drive/start` | Admin auth | Initiate Google Drive OAuth flow. |
| GET | `/admin/google-drive/callback` | Admin auth | OAuth callback handler; persists credentials and optionally hot-reloads config. |
| GET/POST/PUT/DELETE | `/admin/users[/{id}]` | Admin auth | CRUD for managed admin users (via AdminIdentityService). |
| GET/POST/PUT/DELETE | `/admin/groups[/{id}]` | Admin auth | CRUD for managed admin groups. |
| GET/POST/DELETE | `/admin/api-keys[/{id}]` | Admin auth | CRUD for managed admin API keys. |
| GET/POST/PUT/DELETE | `/admin/profiles[/{id}]` | Admin auth | CRUD for storage profiles (DB-backed dynamic profiles). |
| GET | `/admin/runtime-config` | Admin auth | Runtime configuration introspection. |
| GET | `/admin/identity` | Admin token | Identity management admin UI (HTML). |

### Jobs API
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/jobs` | API key | List managed jobs with optional filters (`status`, `session_id`, `job_type`, `limit`). |
| GET | `/api/v1/jobs/queue/status` | API key | Queue backend counters (pending, running, completed, failed). |
| GET | `/api/v1/jobs/{job_id}` | API key | Lookup a specific managed job by ID. |

### Auth (WebUI session)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | Credentials | Cookie-based login for the embedded WebUI. |
| GET | `/auth/me` | Cookie/API key | Current session/user info. |
| POST | `/auth/logout` | Cookie | Destroy web session. |

### Other
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/openapi.json` | None | Generated OpenAPI schema for the tool surface. |
| GET | `/runtime-config.js` | None | Runtime configuration payload for the embedded SPA. |
| GET | `/ui/**`, `/admin/**` (HTML) | None/Cookie | Embedded SPA WebUI; static assets and SPA index fallback. |

## MCP Tool Surface (65 tools)

### File I/O (10 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `read_file` | Read a text file | No | No |
| `write_file` | Write text to a file | Yes | Yes |
| `delete_file` | Delete a file | Yes | Yes |
| `copy_file` | Copy a file | Yes | Yes |
| `move_file` | Move a file or directory | Yes | Yes |
| `move_path` | Move a file or directory (alias) | Yes | Yes |
| `rename_path` | Rename a file or directory | Yes | Yes |
| `create_dir` | Create a directory | Yes | Yes |
| `chmod_path` | Change file or directory mode | Yes | Yes |
| `list_dir` | List directory entries | No | No |

### Search (2 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `search_paths` | Search file paths | No | No |
| `search_content` | Search file contents | No | No |

### Base64 Encoding (4 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `b64_encode` | Encode text as base64 | No | No |
| `b64_decode` | Decode base64 to text | No | No |
| `b64_encode_file` | Encode file contents as base64 | No | No |
| `b64_decode_to_file` | Decode base64 to file | Yes | Yes |

### Validation (2 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `validate_text` | Validate text content by type | No | No |
| `validate_file` | Validate file content by detected or explicit type | No | No |

### In-Memory Structured Editing (13 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `json_get` | Get JSON value by path | No | No |
| `json_set` | Set JSON value by path | Yes | No |
| `json_delete` | Delete JSON value by path | Yes | No |
| `json_copy` | Copy JSON value by path | Yes | No |
| `json_move` | Move JSON value by path | Yes | No |
| `json_merge` | Merge JSON value by path | Yes | No |
| `yaml_get` | Get YAML value by path | No | No |
| `yaml_set` | Set YAML value by path | Yes | No |
| `yaml_delete` | Delete YAML value by path | Yes | No |
| `yaml_copy` | Copy YAML value by path | Yes | No |
| `yaml_move` | Move YAML value by path | Yes | No |
| `yaml_merge` | Merge YAML value by path | Yes | No |
| `replace_regex` | Apply regex replacement | Yes | No |

### Markdown Editing (2 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `markdown_get_section` | Extract markdown section | No | No |
| `markdown_set_section` | Replace markdown section | Yes | No |

### File-Backed Structured Editing (13 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `json_get_file` | Get JSON value from file by path | No | No |
| `json_set_file` | Set JSON value in file with validation/audit/snapshot | Yes | Yes |
| `json_copy_file` | Copy JSON value in file | Yes | Yes |
| `json_move_file` | Move JSON value in file | Yes | Yes |
| `json_merge_file` | Merge JSON value in file | Yes | Yes |
| `yaml_get_file` | Get YAML value from file by path | No | No |
| `yaml_set_file` | Set YAML value in file | Yes | Yes |
| `yaml_delete_file` | Delete YAML value in file | Yes | Yes |
| `yaml_copy_file` | Copy YAML value in file | Yes | Yes |
| `yaml_move_file` | Move YAML value in file | Yes | Yes |
| `yaml_merge_file` | Merge YAML mapping into file | Yes | Yes |
| `xml_set_file` | Set XML value in file | Yes | Yes |
| `html_set_file` | Set HTML value in file | Yes | Yes |

### Markdown File Editing (2 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `markdown_set_section_file` | Set markdown section in file | Yes | Yes |
| `markdown_set_frontmatter_file` | Update markdown YAML frontmatter | Yes | Yes |

### Sed-like File Editing (1 tool)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `sed_edit_file` | Apply sed-like file edits with audit/snapshot support | Yes | Yes |

### Diff and Comparison (3 tools)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `diff_text` | Generate unified diff for text | No | No |
| `diff_files` | Generate unified diff for files | No | No |
| `meld_files` | Launch meld for file comparison (optional integration) | No | No |

### Conversion (1 tool)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `convert_file` | Convert file with limits and warning-based optional backend handling | No | No |

### Backend Status (1 tool)
| Tool | Description | Mutating | Dry-run |
|------|-------------|----------|---------|
| `backend_status` | Return endpoint health states for configured storage backends | No | No |

### Admin Identity (11 tools, conditional)
These tools are registered only when the `AdminIdentityService` is available (requires DB runtime).

| Tool | Description | Mutating |
|------|-------------|----------|
| `admin_list_users` | List managed admin users | No |
| `admin_create_user` | Create managed admin user | Yes |
| `admin_update_user` | Update managed admin user | Yes |
| `admin_delete_user` | Delete managed admin user | Yes |
| `admin_list_groups` | List managed admin groups | No |
| `admin_create_group` | Create managed admin group | Yes |
| `admin_update_group` | Update managed admin group | Yes |
| `admin_delete_group` | Delete managed admin group | Yes |
| `admin_list_api_keys` | List managed admin API keys | No |
| `admin_create_api_key` | Create managed admin API key | Yes |
| `admin_revoke_api_key` | Revoke managed admin API key | Yes |

## Example: MCP Tool Call (streamable-HTTP)
```bash
curl -X POST http://localhost:8083/mcp \
  -H "Content-Type: application/json" \
  -H "Authorisation: Bearer your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"path": "/tmp/example.txt"}
    }
  }'
```

## Example: List Available Tools
```bash
curl http://localhost:8083/mcp/tools
```

## Example: Health Check
```bash
curl http://localhost:8083/health
```

```json
{
  "status": "ok",
  "service": "file-mcp-server",
  "profile": "default",
  "endpoint_health": {}
}
```
