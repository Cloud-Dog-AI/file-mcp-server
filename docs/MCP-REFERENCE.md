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
