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
doc-last-updated: 2026-06-12
doc-git-commit: 708278bca73b1a0cbdb03f1b108122d55cfd259e
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# file-mcp-server — MCP-REFERENCE

> **Template version:** T-MCP v1.0 — MCP tool surface (JSON-RPC 2.0 at `/mcp`).

## 1. Auth model
MCP auth mode (`api_key` typically); header form; how RBAC maps from API key to MCP tool visibility.

## 2. Tools

**You MUST include:** every tool exposed by `tools/list`. One section per tool.

### 2.1 `<tool_name>`
- **Description:** <one line>
- **RBAC:** roles allowed (admin / read-write / read-only / ...)
- **Input schema:**
  ```json
  { "type": "object", "properties": { ... } }
  ```
- **Output schema:**
  ```json
  { "type": "object", "properties": { ... } }
  ```
- **Errors:** <typed error catalogue>
- **Example call:**
  ```bash
  curl -X POST https://<host>/mcp \
    -H "Accept: application/json, text/event-stream" \
    -H "X-API-Key: ${API_KEY}" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"<tool_name>","arguments":{...}},"id":1}'
  ```

## 3. Cross-references
- [API-REFERENCE.md](API-REFERENCE.md)
- [A2A-REFERENCE.md](A2A-REFERENCE.md)
- PS-72-mcp-a2a-webui.md

## 4. Project-specific notes



<!-- W28C-1710a recovery: full content from archive/2026-06-12/MCP_DOCUMENTATION.md (archived sha256=14e1ea9e8b4a, 107 lines) -->

## Recovered domain content — `archive/2026-06-12/MCP_DOCUMENTATION.md` (107 lines)

_This section carries forward the full content of the archived predecessor doc verbatim. Topic checklist + SHA256 chain in `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/file-mcp-server/MCP_DOCUMENTATION.md.topics.tsv`. Archive contents are unchanged (sha256 stable)._

# MCP Server Documentation

## Transport
Primary transport: Streamable HTTP at `/mcp` unless the service documents an alternative mode in its runtime configuration.

## Authentication
Use `X-API-Key: <your-api-key>` on protected HTTP and MCP endpoints.

## Verification Basis
- Source files reviewed: `src/file_mcp_server/server.py`
- Tool inventory size: 65

## Tools
| Tool | Notes |
|------|-------|
| `admin_create_api_key` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_create_group` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_create_user` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_delete_group` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_delete_user` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_list_api_keys` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_list_groups` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_list_users` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_revoke_api_key` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_update_group` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_update_user` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `b64_decode` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `b64_decode_to_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `b64_encode` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `b64_encode_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `backend_status` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `chmod_path` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `convert_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `copy_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `create_dir` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `delete_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `diff_files` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `diff_text` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `html_set_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_copy` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_copy_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_get_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_merge` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_merge_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_move` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_move_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_set` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `json_set_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `list_dir` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `markdown_get_section` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `markdown_set_frontmatter_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `markdown_set_section` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `markdown_set_section_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `meld_files` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `move_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `move_path` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `read_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `rename_path` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `replace_regex` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `search_content` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `search_paths` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `sed_edit_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `validate_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `validate_text` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `write_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `xml_set_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_copy` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_copy_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_delete_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_get_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_merge` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_merge_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_move` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_move_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_set` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `yaml_set_file` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |

## Example Call
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/list",
  "params": {}
}
```

## Example Response
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "tools": [
      {
        "name": "tool_name",
        "description": "What the tool does",
        "inputSchema": {"type": "object"}
      }
    ]
  }
}
```
