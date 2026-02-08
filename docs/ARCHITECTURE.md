# File MCP Server — ARCHITECTURE.md
Version: 0.3 • 2026-02-08
Status: Active

## 1. System Overview
`file-mcp-server` is a transport-facing MCP service backed by a reusable `file_tools` library.

Design goals:
- deterministic file operations inside configured scope
- strict auth + scope policy enforcement
- mutation auditability and optional snapshots
- tool reuse outside server runtime

Out of scope:
- LLM/model integration
- internet crawling/search

## 2. Runtime Architecture

### 2.1 Layers
- `src/file_tools/*`: reusable domain modules (config, scope, IO, edit, search, validate, convert, audit, diff)
- `src/file_mcp_server/*`: transport/auth/dispatch lifecycle layer

### 2.2 Core Runtime Flow
1. Load config via precedence chain.
2. Select profile.
3. Build auth verifier and tool registry.
4. For each call: authenticate -> scope-check -> execute handler -> return structured output/error.
5. For mutating calls: optional snapshot + validation + append-only audit event.

### 2.3 Key Modules
- `src/file_mcp_server/server.py`: FastMCP transport wiring, middleware, tool registration, file-level handlers.
- `src/file_mcp_server/main.py`: CLI commands (`serve`, `start`, `stop`, `status`).
- `src/file_mcp_server/lifecycle.py`: pidfile and lifecycle primitives.
- `src/file_tools/config/loader.py`: environment/config precedence and profile loading.
- `src/file_tools/scope/policy.py`: path and allow/deny enforcement.
- `src/file_tools/audit/*`: audit event model + snapshot retention.

## 3. Configuration Model

### 3.1 Precedence
1. `os.environ`
2. `--env-path` file
3. `config.yaml`
4. `defaults.yaml`

### 3.2 Profile Areas
- `auth`: API keys, header name/scheme
- `scope`: roots, allow/deny globs, extension constraints
- `audit`: log path and options
- `snapshots`: mode + retention (`days`, `count`, `max_storage_mb`)
- `validation`: per-type policy (`strict` / `warn` / `ignore`)
- `limits`: search limits (`max_results`, `max_file_mb`, `search_timeout_s`) and conversion timeout
- `conversion`: backends and input-size limit

## 4. Transport & Interface

### 4.1 Supported HTTP Modes
Configured by `http.transport`:
- `streamable-http` (default): MCP streamable HTTP endpoint on `http.mcp_path` (default `/mcp`)
- `http`: non-streaming MCP HTTP endpoint on `http.mcp_path`
- `sse`: SSE endpoint on `http.events_path` (default `/events`)

Health endpoint:
- `GET http.health_path` (default `/health`)

### 4.2 Authentication
- API key required for tool calls.
- Header name and scheme are profile-configurable.
- Raw secrets are never written to logs.

## 5. Tool Surface

Tool groups:
- filesystem (`read_file`, `write_file`, `copy_file`, `move_file`, `delete_file`, `list_dir`)
- search (`search_paths`, `search_content`)
- structured text/object operations (`json_*`, `yaml_*`, `xml_set_file`, `html_set_file`, `markdown_*`)
- sed-like edits (`sed_edit_file`)
- validate (`validate_text`, `validate_file`)
- conversion (`convert_file`)
- diff and optional GUI compare (`diff_text`, `diff_files`, `meld_files`)
- base64 operations (`b64_*`)

Mutating operations support `dry_run` where deterministic preview is possible.

## 6. Data Safety & Integrity

### 6.1 Scope Enforcement
- normalize + root-bound checks
- allow/deny glob checks
- extension constraints
- no traversal/cross-root escape

### 6.2 Mutation Safety
- atomic write path in IO layer
- configurable post-edit validation
- append-only audit entries for all mutation attempts
- snapshot creation before change when enabled

### 6.3 Snapshot Retention
Retention supports:
- `retention_days`
- `retention_count`
- `max_storage_mb`

Applied in prune order: age -> count -> size.

## 7. Search Model
- path and content search across scoped roots
- optional `max_depth` traversal control
- optional `timeout_s` operation bound
- respects deny patterns and file-size/result limits

## 8. Operations & Lifecycle

### 8.1 CLI
- `python -m file_mcp_server serve ...`
- `python -m file_mcp_server start ...`
- `python -m file_mcp_server stop ...`
- `python -m file_mcp_server status ...`

### 8.2 Lifecycle Script
Project-provided wrapper:
- `./server_control.sh --env <env-file> start|stop|status|restart|serve`

`--env` is required by design for explicit operational context.

## 9. Testing Architecture
- Unit tests for module correctness.
- System tests for runtime contracts.
- Integration tests for multi-module behavior over real HTTP tool calls.
- Application tests for realistic multi-step workflows.

Current baseline: full suite green (`132 passed`).

## 10. Documentation Map
- Requirements: `docs/REQUIREMENTS.md`
- Tasks traceability: `docs/TASKS.md`
- Test traceability + run evidence: `docs/TESTS.md`
- API contract summary: `API_DOCUMENTATION.md` and `openapi.json`
