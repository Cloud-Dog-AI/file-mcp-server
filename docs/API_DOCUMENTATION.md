# API Documentation

## Base URLs
- Local development: `http://localhost:8083`
- Deployed: `https://file-mcp.your-domain.com`

## Authentication
Use `Authorization: Bearer <your-api-key>` or `X-API-Key: <your-api-key>` on protected HTTP and MCP endpoints.

## Verification Basis
- Source files reviewed: `src/file_mcp_server/server.py`
- Route inventory size: 9

## Route Inventory
| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Public health endpoint |
| GET | `/ready` | Public readiness endpoint |
| GET | `/live` | Public liveness endpoint |
| GET | `/status` | Extended status endpoint |
| POST | `/mcp` | Primary MCP transport endpoint |
| GET | `/sse` | Legacy SSE stream |
| POST | `/messages` | Legacy JSON-RPC message endpoint |
| GET | `/a2a` | A2A root endpoint |
| GET | `/a2a/events` | A2A event feed |

## Example Request
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8083/health
```

## Example Response
```json
{
  "ok": true,
  "result": {
    "status": "healthy"
  }
}
```
