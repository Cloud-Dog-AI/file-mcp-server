---
template-id: T-MCP
template-version: 1.0
applies-to: docs/MCP-REFERENCE.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 24cd1ac046fd3b0da63e4dcfc9cbdc0188ca6947
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T09:40:00Z
---

# file-mcp-server — MCP-REFERENCE

> **Template version:** T-MCP v1.0 — MCP tool surface (JSON-RPC 2.0 at `/mcp`).

## 1. Auth model

- **Transport:** Streamable HTTP at `/mcp`; legacy SSE also supported. Browser WebUI uses `/webmcp`.
- **Header:** `Authorisation: Bearer <api-key>` or `X-API-Key: <api-key>`.
- **RBAC:** All tools are available to any authenticated caller. Write/mutation tools are blocked for `read-only` role callers by the `guard.py` layer. Admin identity tools (`admin_*`) require `admin` role.
- **Session (WebUI):** Cookie-based (`file_web_session`; `HttpOnly; SameSite=Lax`). The `/webmcp` path accepts the session cookie in lieu of an API key.

## 2. Tools

65 tools total: 54 core tools + 11 conditional admin identity tools (registered when `AdminIdentityService` is enabled via DB runtime).

### 2.1 `read_file`
- **Description:** Read a text file and return its content.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "encoding": {"type": "string", "default": "utf-8"},
      "start_line": {"type": "integer"},
      "end_line": {"type": "integer"},
      "start_byte": {"type": "integer"},
      "end_byte": {"type": "integer"}
    },
    "required": ["path"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"content": {"type": "string"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`, `encoding_error`
- **Example call:**
  ```bash
  curl -X POST https://<host>/mcp \
    -H "Authorisation: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"read_file","arguments":{"path":"/data/example.txt"}},"id":1}'
  ```

### 2.2 `write_file`
- **Description:** Write text to a file. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "content": {"type": "string"},
      "encoding": {"type": "string", "default": "utf-8"},
      "overwrite": {"type": "boolean", "default": true},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["path", "content"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}, "job_id": {"type": "string"}}}`
- **Errors:** `permission_denied`, `scope_violation`, `overwrite_denied`, `dry_run_result`

### 2.3 `delete_file`
- **Description:** Delete a file. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "missing_ok": {"type": "boolean", "default": false},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["path"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"deleted": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`

### 2.4 `copy_file`
- **Description:** Copy a file to a new destination. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "src": {"type": "string"},
      "dst": {"type": "string"},
      "overwrite": {"type": "boolean", "default": false},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["src", "dst"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"copied": {"type": "boolean"}, "src": {"type": "string"}, "dst": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`, `overwrite_denied`

### 2.5 `move_file`
- **Description:** Move a file or directory. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "src": {"type": "string"},
      "dst": {"type": "string"},
      "overwrite": {"type": "boolean", "default": false},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["src", "dst"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"moved": {"type": "boolean"}, "src": {"type": "string"}, "dst": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`

### 2.6 `move_path`
- **Description:** Move a file or directory (alias of `move_file` with consistent parameter naming). Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:** Same as `move_file`.
- **Output schema:** Same as `move_file`.
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`

### 2.7 `rename_path`
- **Description:** Rename a file or directory within the same parent directory. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "src": {"type": "string"},
      "dst": {"type": "string"},
      "overwrite": {"type": "boolean", "default": false},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["src", "dst"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"renamed": {"type": "boolean"}, "src": {"type": "string"}, "dst": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`

### 2.8 `create_dir`
- **Description:** Create a directory (with optional parents). Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "parents": {"type": "boolean", "default": true},
      "exist_ok": {"type": "boolean", "default": true},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["path"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"created": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `permission_denied`, `scope_violation`

### 2.9 `chmod_path`
- **Description:** Change file or directory mode bits. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "mode": {"type": "string"},
      "recursive": {"type": "boolean", "default": false},
      "dry_run": {"type": "boolean", "default": false}
    },
    "required": ["path", "mode"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"changed": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`, `invalid_mode`

### 2.10 `list_dir`
- **Description:** List directory entries, optionally recursive.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "recursive": {"type": "boolean", "default": false}
    },
    "required": ["path"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"entries": {"type": "array"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `permission_denied`, `scope_violation`

### 2.11 `search_paths`
- **Description:** Search file paths by name glob or regex within allowed scope roots.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "glob": {"type": "string"},
      "regex": {"type": "boolean", "default": false},
      "max_results": {"type": "integer"},
      "max_file_mb": {"type": "number"},
      "max_depth": {"type": "integer"},
      "timeout_s": {"type": "number"}
    },
    "required": ["query"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"results": {"type": "array"}, "truncated": {"type": "boolean"}}}`
- **Errors:** `scope_violation`, `timeout`

### 2.12 `search_content`
- **Description:** Search file contents by text query or regex.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "glob": {"type": "string"},
      "regex": {"type": "boolean", "default": false},
      "max_results": {"type": "integer"},
      "encoding": {"type": "string", "default": "utf-8"},
      "max_file_mb": {"type": "number"},
      "max_depth": {"type": "integer"},
      "timeout_s": {"type": "number"}
    },
    "required": ["query"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"results": {"type": "array"}, "truncated": {"type": "boolean"}}}`
- **Errors:** `scope_violation`, `timeout`, `encoding_error`

### 2.13 `b64_encode`
- **Description:** Encode a text string as base64.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "urlsafe": {"type": "boolean", "default": false}}, "required": ["text"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `encoding_error`

### 2.14 `b64_decode`
- **Description:** Decode a base64 string to text.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"data": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "urlsafe": {"type": "boolean", "default": false}}, "required": ["data"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `decode_error`

### 2.15 `b64_encode_file`
- **Description:** Read a file and return its contents as base64.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "urlsafe": {"type": "boolean", "default": false}}, "required": ["path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`

### 2.16 `b64_decode_to_file`
- **Description:** Decode a base64 string and write the result to a file. Supports managed jobs when enabled. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "data": {"type": "string"}, "urlsafe": {"type": "boolean", "default": false}, "overwrite": {"type": "boolean", "default": true}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "data"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}, "job_id": {"type": "string"}}}`
- **Errors:** `permission_denied`, `scope_violation`, `decode_error`

### 2.17 `validate_text`
- **Description:** Validate text content against a named type (json, yaml, xml, html, markdown).
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"content_type": {"type": "string"}, "text": {"type": "string"}}, "required": ["content_type", "text"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"valid": {"type": "boolean"}, "errors": {"type": "array"}}}`
- **Errors:** `unknown_content_type`

### 2.18 `validate_file`
- **Description:** Validate file content by detected or explicit type.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "content_type": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"valid": {"type": "boolean"}, "errors": {"type": "array"}, "detected_type": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `unknown_content_type`

### 2.19 `json_get`
- **Description:** Get a value from a JSON string by path.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}}, "required": ["text", "path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"value": {}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.20 `json_set`
- **Description:** Set a value in a JSON string by path and return the modified JSON.
- **RBAC:** admin / read-write / read-only (in-memory only; no file write)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}, "value": {}}, "required": ["text", "path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`

### 2.21 `json_delete`
- **Description:** Delete a value from a JSON string by path and return the modified JSON.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}}, "required": ["text", "path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.22 `json_copy`
- **Description:** Copy a JSON value from one path to another within a JSON string.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}}, "required": ["text", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.23 `json_move`
- **Description:** Move a JSON value from one path to another within a JSON string.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}}, "required": ["text", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.24 `json_merge`
- **Description:** Merge a value into a JSON string at a given path.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}, "value": {}}, "required": ["text", "path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`

### 2.25 `yaml_get`
- **Description:** Get a value from a YAML string by path.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}}, "required": ["text", "path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"value": {}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.26 `yaml_set`
- **Description:** Set a value in a YAML string by path and return the modified YAML.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}, "value": {}}, "required": ["text", "path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`

### 2.27 `yaml_delete`
- **Description:** Delete a value from a YAML string by path.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}}, "required": ["text", "path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.28 `yaml_copy`
- **Description:** Copy a YAML value from one path to another within a YAML string.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}}, "required": ["text", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.29 `yaml_move`
- **Description:** Move a YAML value from one path to another within a YAML string.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}}, "required": ["text", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`, `path_not_found`

### 2.30 `yaml_merge`
- **Description:** Merge a mapping into a YAML string at a given path.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "path": {"type": "string"}, "value": {}}, "required": ["text", "path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `parse_error`

### 2.31 `replace_regex`
- **Description:** Apply a regex substitution to a text string and return the result.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "pattern": {"type": "string"}, "repl": {"type": "string"}, "count": {"type": "integer", "default": 0}}, "required": ["text", "pattern", "repl"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}, "count": {"type": "integer"}}}`
- **Errors:** `invalid_regex`

### 2.32 `markdown_get_section`
- **Description:** Extract the content of a named section from a Markdown string.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "heading": {"type": "string"}}, "required": ["text", "heading"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"content": {"type": "string"}}}`
- **Errors:** `section_not_found`

### 2.33 `markdown_set_section`
- **Description:** Replace the content of a named section in a Markdown string.
- **RBAC:** admin / read-write / read-only (in-memory only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"text": {"type": "string"}, "heading": {"type": "string"}, "new_content": {"type": "string"}}, "required": ["text", "heading", "new_content"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"result": {"type": "string"}}}`
- **Errors:** `section_not_found`

### 2.34 `json_get_file`
- **Description:** Get a JSON value from a file by path expression.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "json_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path", "json_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"value": {}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.35 `json_set_file`
- **Description:** Set a JSON value in a file at a given path; creates audit log and snapshot. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "json_path": {"type": "string"}, "value": {}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "json_path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`

### 2.36 `json_copy_file`
- **Description:** Copy a JSON value within a file from one path to another. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.37 `json_move_file`
- **Description:** Move a JSON value within a file from one path to another. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.38 `json_merge_file`
- **Description:** Merge a JSON value into a file at a given path. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "value": {}, "json_path": {"type": "string", "default": "/"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`

### 2.39 `yaml_get_file`
- **Description:** Get a YAML value from a file by path expression.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "yaml_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path", "yaml_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"value": {}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.40 `yaml_set_file`
- **Description:** Set a YAML value in a file at a given path. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "yaml_path": {"type": "string"}, "value": {}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "yaml_path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`

### 2.41 `yaml_delete_file`
- **Description:** Delete a YAML value in a file at a given path. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "yaml_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "yaml_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.42 `yaml_copy_file`
- **Description:** Copy a YAML value within a file from one path to another. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.43 `yaml_move_file`
- **Description:** Move a YAML value within a file from one path to another. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "from_path": {"type": "string"}, "to_path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "from_path", "to_path"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `path_not_found`

### 2.44 `yaml_merge_file`
- **Description:** Merge a YAML mapping into a file at a given path. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "value": {}, "yaml_path": {"type": "string", "default": "/"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`

### 2.45 `xml_set_file`
- **Description:** Set an XML value in a file using an XPath selector. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "xpath": {"type": "string"}, "value": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "xpath", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `xpath_error`

### 2.46 `html_set_file`
- **Description:** Set an HTML element value in a file using a CSS selector. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "selector": {"type": "string"}, "value": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "selector", "value"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`, `selector_not_found`

### 2.47 `markdown_set_section_file`
- **Description:** Replace the content of a named section in a Markdown file. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "heading": {"type": "string"}, "new_content": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "heading", "new_content"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `section_not_found`

### 2.48 `markdown_set_frontmatter_file`
- **Description:** Update YAML frontmatter in a Markdown file. Supports dry-run.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path": {"type": "string"}, "updates": {"type": "object"}, "encoding": {"type": "string", "default": "utf-8"}, "dry_run": {"type": "boolean", "default": false}}, "required": ["path", "updates"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `parse_error`

### 2.49 `sed_edit_file`
- **Description:** Apply sed-like edits to a file (substitution, line insert/delete/replace). Supports audit, snapshot, and dry-run. Accepts a list of operations for batch editing.
- **RBAC:** admin / read-write (blocked for read-only)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "op": {"type": "string", "enum": ["substitute", "insert", "delete", "replace"]},
      "pattern": {"type": "string"},
      "repl": {"type": "string"},
      "count": {"type": "integer", "default": 0},
      "line_no": {"type": "integer"},
      "content": {"type": "string"},
      "start": {"type": "integer"},
      "end": {"type": "integer"},
      "replacement": {"type": "string"},
      "operations": {"type": "array"},
      "dry_run": {"type": "boolean", "default": false},
      "encoding": {"type": "string", "default": "utf-8"}
    },
    "required": ["path"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"written": {"type": "boolean"}, "path": {"type": "string"}, "changes": {"type": "integer"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `invalid_regex`

### 2.50 `diff_text`
- **Description:** Generate a unified diff between two text strings.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"before": {"type": "string"}, "after": {"type": "string"}, "context": {"type": "integer", "default": 3}}, "required": ["before", "after"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"diff": {"type": "string"}}}`
- **Errors:** none

### 2.51 `diff_files`
- **Description:** Generate a unified diff between two files.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path_a": {"type": "string"}, "path_b": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}, "context": {"type": "integer", "default": 3}}, "required": ["path_a", "path_b"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"diff": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`

### 2.52 `meld_files`
- **Description:** Launch `meld` for visual file comparison (optional integration; no-op if meld not installed).
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"path_a": {"type": "string"}, "path_b": {"type": "string"}}, "required": ["path_a", "path_b"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"launched": {"type": "boolean"}}}`
- **Errors:** `meld_not_available`, `file_not_found`

### 2.53 `convert_file`
- **Description:** Convert a file to another format using configured conversion backends (e.g. Pandoc). Supports managed jobs when enabled. Configurable limits and timeout.
- **RBAC:** admin / read-write / read-only
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "target_format": {"type": "string"},
      "output_path": {"type": "string"},
      "max_input_mb": {"type": "number"},
      "timeout_s": {"type": "number"},
      "simulate_delay_s": {"type": "number"},
      "backend": {"type": "string"}
    },
    "required": ["path", "target_format"]
  }
  ```
- **Output schema:** `{"type": "object", "properties": {"converted": {"type": "boolean"}, "output_path": {"type": "string"}, "job_id": {"type": "string"}}}`
- **Errors:** `file_not_found`, `scope_violation`, `conversion_error`, `timeout`, `backend_unavailable`

### 2.54 `backend_status`
- **Description:** Return health states for all configured storage backends (local, S3, WebDAV, FTP, Google Drive).
- **RBAC:** admin / read-write / read-only
- **Input schema:** `{"type": "object", "properties": {}}`
- **Output schema:** `{"type": "object", "properties": {"backends": {"type": "object"}, "overall": {"type": "string"}}}`
- **Errors:** none (always returns, errors per-backend)

### 2.55 `admin_list_users` _(conditional — requires AdminIdentityService)_
- **Description:** List all managed admin users.
- **RBAC:** admin only
- **Input schema:** `{"type": "object", "properties": {}}`
- **Output schema:** `{"type": "object", "properties": {"users": {"type": "array"}}}`
- **Errors:** `admin_identity_unavailable`

### 2.56 `admin_create_user` _(conditional — requires AdminIdentityService)_
- **Description:** Create a new managed admin user.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"username": {"type": "string"}, "password": {"type": "string"}, "role": {"type": "string"}, "groups": {"type": "array"}}, "required": ["username", "password"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"user": {"type": "object"}}}`
- **Errors:** `admin_identity_unavailable`, `user_exists`

### 2.57 `admin_update_user` _(conditional — requires AdminIdentityService)_
- **Description:** Update an existing managed admin user's properties.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"user_id": {"type": "string"}, "password": {"type": "string"}, "role": {"type": "string"}, "groups": {"type": "array"}}, "required": ["user_id"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"user": {"type": "object"}}}`
- **Errors:** `admin_identity_unavailable`, `user_not_found`

### 2.58 `admin_delete_user` _(conditional — requires AdminIdentityService)_
- **Description:** Delete a managed admin user.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"deleted": {"type": "boolean"}}}`
- **Errors:** `admin_identity_unavailable`, `user_not_found`

### 2.59 `admin_list_groups` _(conditional — requires AdminIdentityService)_
- **Description:** List all managed admin groups.
- **RBAC:** admin only
- **Input schema:** `{"type": "object", "properties": {}}`
- **Output schema:** `{"type": "object", "properties": {"groups": {"type": "array"}}}`
- **Errors:** `admin_identity_unavailable`

### 2.60 `admin_create_group` _(conditional — requires AdminIdentityService)_
- **Description:** Create a new managed admin group.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}}, "required": ["name"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"group": {"type": "object"}}}`
- **Errors:** `admin_identity_unavailable`, `group_exists`

### 2.61 `admin_update_group` _(conditional — requires AdminIdentityService)_
- **Description:** Update an existing managed admin group.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"group_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}}, "required": ["group_id"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"group": {"type": "object"}}}`
- **Errors:** `admin_identity_unavailable`, `group_not_found`

### 2.62 `admin_delete_group` _(conditional — requires AdminIdentityService)_
- **Description:** Delete a managed admin group.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"group_id": {"type": "string"}}, "required": ["group_id"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"deleted": {"type": "boolean"}}}`
- **Errors:** `admin_identity_unavailable`, `group_not_found`

### 2.63 `admin_list_api_keys` _(conditional — requires AdminIdentityService)_
- **Description:** List all managed admin API keys.
- **RBAC:** admin only
- **Input schema:** `{"type": "object", "properties": {}}`
- **Output schema:** `{"type": "object", "properties": {"api_keys": {"type": "array"}}}`
- **Errors:** `admin_identity_unavailable`

### 2.64 `admin_create_api_key` _(conditional — requires AdminIdentityService)_
- **Description:** Create a new managed admin API key.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "expires_at": {"type": "string"}}, "required": ["name"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"api_key": {"type": "object"}, "key": {"type": "string"}}}`
- **Errors:** `admin_identity_unavailable`

### 2.65 `admin_revoke_api_key` _(conditional — requires AdminIdentityService)_
- **Description:** Revoke a managed admin API key by ID.
- **RBAC:** admin only
- **Input schema:**
  ```json
  {"type": "object", "properties": {"key_id": {"type": "string"}}, "required": ["key_id"]}
  ```
- **Output schema:** `{"type": "object", "properties": {"revoked": {"type": "boolean"}}}`
- **Errors:** `admin_identity_unavailable`, `key_not_found`

## 3. Cross-references
- [API-REFERENCE.md](API-REFERENCE.md)
- [A2A-REFERENCE.md](A2A-REFERENCE.md)
- PS-72-mcp-a2a-webui.md

## 4. Project-specific notes

- All tools are discovered at runtime via `tools/list`; the count may vary if the `AdminIdentityService` is not available (54 core vs 65 with admin identity).
- Dry-run support: tools marked "Supports dry-run" accept `dry_run=true` and return a simulation result without persisting changes.
- Managed jobs: tools marked "Supports managed jobs" may return a `job_id` when the jobs subsystem is enabled (`FILE_MCP_JOBS_ENABLED=true`). Poll `/api/v1/jobs/{job_id}` for status.
- Scope enforcement: all file-path arguments are validated against the configured `scope.roots` and `scope.allow_globs` / `scope.deny_globs` before execution.
