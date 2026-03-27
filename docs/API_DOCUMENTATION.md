# API Documentation

## Base URLs

| Surface | Default Port | Local URL |
|---------|-------------|-----------|
| API Server | 8060 | `http://localhost:8060` |
| Web Server | 8061 | `http://localhost:8061` |
| MCP Server | 8062 | `http://localhost:8062` |
| A2A Server | 8063 | `http://localhost:8063` |

Deployed: `https://file-mcp.your-domain.com`

## Authentication

- **API Key:** `X-API-Key: <your-api-key>` or `Authorization: Bearer <your-api-key>`
- Key configured via `profiles.<name>.auth.api_keys` in config

## Endpoints

The file-mcp-server exposes tools via the MCP protocol rather than traditional REST routes. The API, Web, MCP, and A2A surfaces are selected via `--server-role` (api, web, mcp, a2a).

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Service health check |
| GET | /ready | No | Readiness probe |
| GET | /live | No | Liveness probe |
| GET | /status | No | Extended status |

### MCP Transport (MCP Server surface, port 8062)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /mcp | API Key | Streamable HTTP MCP endpoint |
| GET | /sse | API Key | Legacy SSE stream |
| POST | /messages | API Key | Legacy JSON-RPC messages |

### MCP Tools (via MCP protocol)

The following tools are available through the MCP transport:

| Tool | Description |
|------|-------------|
| read_file | Read file content |
| write_file | Write content to a file |
| b64_decode_to_file | Decode base64 and write to file |
| b64_encode_file | Encode file content as base64 |
| list_directory | List directory contents |
| search_files | Search files by name pattern |
| search_content | Search file content with regex |
| get_file_info | Get file metadata |
| move_file | Move or rename a file |
| copy_file | Copy a file |
| delete_file | Delete a file |
| create_directory | Create a directory |
| tree | Directory tree listing |
| calculate_hash | Calculate file hash |
| validate_file | Validate file content (JSON, YAML, XML) |
| convert_file | Convert file format |
| snapshot_create | Create a file snapshot |
| snapshot_list | List snapshots |
| snapshot_restore | Restore a snapshot |

### A2A (A2A Server surface, port 8063)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /a2a | API Key | A2A root info |
| GET | /a2a/events | API Key | A2A configuration events |
| WS | /a2a/events | API Key | WebSocket for real-time events |
