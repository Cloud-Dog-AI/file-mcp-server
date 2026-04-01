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
