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
| `b64_decode_to_file` | Decode base64 to file | yes | `path, data, urlsafe=False, overwrite=True, dry_run=False` | JSON object; schema depends on tool |
| `b64_encode` | Encode text as base64 | no | `text, encoding='utf-8', urlsafe=False` | JSON object; schema depends on tool |
| `b64_encode_file` | Encode file contents as base64 | no | `path, urlsafe=False` | JSON object; schema depends on tool |
| `backend_status` | Return endpoint health states for configured storage backends | no | `-` | JSON object; schema depends on tool |
| `chmod_path` | Change file or directory mode | yes | `path, mode, recursive=False, dry_run=False` | JSON object; schema depends on tool |
| `convert_file` | Convert file with limits and warning-based optional backend handling | no | `path, target_format, output_path=None, max_input_mb=None, timeout_s=None, simulate_delay_s=None, backend=None` | JSON object; schema depends on tool |
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
| `GET` | `/a2a/health` | A2A health contract in local runtime test mode | Required (`Authorization: Bearer <API key>`) | `200` with valid key, `401` otherwise |

## 4. Error Contract

- MCP tool errors are returned as structured JSON-RPC errors.
- REST/admin endpoints use structured JSON error payloads aligned to platform API standards.
- Common failure classes: auth failure, scope validation, backend unavailable, validation failure, timeout.
