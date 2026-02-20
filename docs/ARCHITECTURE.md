# File MCP Server — ARCHITECTURE.md
Version: 0.6 • 2026-02-19
Status: Active (Release Candidate)

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
1. Load config through `file_tools.config.adapter`, which delegates to `cloud_dog_config` (PS-80 precedence/compile).
2. Load all configured profiles and set a server default profile.
3. Resolve active profile per request (query/header with default fallback), then apply profile-aware auth and registry routing.
4. Run endpoint health startup checks for configured backends.
5. Configure structured operational/audit logging through `cloud_dog_logging` (PS-40) using loaded profile config paths/levels.
6. For each call: authenticate -> scope-check -> backend health gate -> execute handler -> return structured output/error.
7. Propagate correlation ID through request middleware into app + audit entries for tool call/result tracing.
8. For mutating calls: optional snapshot + validation + append-only audit event.

### 2.3 Key Modules
- `src/file_mcp_server/server.py`: FastMCP transport wiring, middleware, tool registration, file-level handlers.
- `src/file_mcp_server/server.py`: compatibility export layer (thin module, migration-safe import surface).
- `src/file_mcp_server/server_runtime.py`: FastMCP transport wiring, middleware, tool registration, file-level handlers.
- `src/file_mcp_server/main.py`: CLI commands (`serve`, `start`, `stop`, `status`).
- `src/file_mcp_server/lifecycle.py`: pidfile and lifecycle primitives.
- `src/file_mcp_server/endpoint_health.py`: endpoint probe/retry/recovery manager.
- `src/file_tools/config/adapter.py`: `cloud_dog_config` bridge that binds output into `ServerConfig`.
- `cloud_dog_config`: platform config package handling precedence, compile, Vault expressions, and immutable snapshots.
- `src/file_tools/observability.py`: bridge configuring PS-40 logging from loaded `ProfileConfig`.
- `src/file_tools/audit/adapter.py`: audit compatibility adapter mapping domain events to PS-40 audit schema.
- `cloud_dog_logging`: platform logging package handling JSONL formatting, redaction, sinks, and correlation context.
- `src/file_tools/scope/policy.py`: path and allow/deny enforcement.
- `src/file_tools/audit/snapshots.py`: domain snapshot lifecycle/retention.
- `src/file_tools/storage/google_drive.py`: Google Drive backend implementation.

## 3. Configuration Model

### 3.1 Precedence
1. `os.environ`
2. `--env-path` file
3. `config.yaml`
4. `defaults.yaml`

### 3.2 Profile Areas
- `auth`: API keys, header name/scheme
- `storage`: backend selection (local/s3/webdav/ftp/google_drive) and TLS controls
- `scope`: roots, allow/deny globs, extension constraints
- `audit`: log path and options
- `snapshots`: mode + retention (`days`, `count`, `max_storage_mb`)
- `validation`: per-type policy (`strict` / `warn` / `ignore`)
- `limits`: search limits (`max_results`, `max_file_mb`, `search_timeout_s`), storage timeout, and conversion timeout
- `conversion`: backends and input-size limit
- `endpoint_health`: startup checks, retry policy, recovery cooldown, restart threshold
  - includes optional process-exit policy (`restart_on_threshold`, `restart_exit_code`)

## 4. Transport & Interface

### 4.1 Supported HTTP Modes
Configured by `http.transport`:
- `streamable-http` (default): MCP streamable HTTP endpoint on `http.mcp_path` (default `/mcp`)
- `http`: non-streaming MCP HTTP endpoint on `http.mcp_path`
- `sse`: SSE endpoint on `http.events_path` (default `/events`)

Health endpoint:
- `GET http.health_path` (default `/health`)
- `GET /ready`
- `GET /live`
- Admin endpoints (when enabled):
  - `GET /admin/google-drive`
  - `POST /admin/google-drive/start`
  - `GET /admin/google-drive/callback`
  - `POST /admin/reload`

### 4.2 Authentication
- API key required for tool calls.
- Header name and scheme are profile-configurable.
- Validation is profile-aware: selected-profile keys are accepted, cross-profile keys are rejected.
- Raw secrets are never written to logs.

### 4.3 Profile Selection
- Server default profile is set by `FILE_MCP_PROFILE` / CLI `--profile`.
- Request-level override is supported by:
  - query parameter `profile=<name>`
  - header `X-File-MCP-Profile: <name>`
- If override is missing or unknown, server default profile is used.

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
- runtime status (`backend_status`)

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

### 8.3 Endpoint Health Lifecycle
- Startup probes evaluate configured backends and classify status (`healthy`, `temporary_unavailable`, `busy_temporary`, `auth_failed`, `failed`).
- Runtime calls trigger delayed recovery attempts for unhealthy backends.
- Endpoint state is queryable via the `backend_status` tool and logged during startup and retries.
- When `restart_on_threshold` is enabled and threshold is reached, the server exits with `restart_exit_code` so an external supervisor/container policy can restart it.

### 8.4 Runtime Reload Lifecycle
- Middleware hosts admin routes for Google Drive onboarding and profile rebinding.
- `POST /admin/reload` rebuilds the active profile registry from current env/config/defaults.
- Reload path reruns endpoint startup checks and updates `backend_status` state.
- Admin route access is explicitly gated by `FILE_MCP_ADMIN_UI_ENABLED` and optional `FILE_MCP_ADMIN_UI_TOKEN`.

## 9. Storage Backend Architecture

### 9.1 Shared Backend Contract
- Backends implement `StorageBackend` with logical POSIX path semantics.
- Unsupported capabilities return deterministic `Not supported for backend` errors.
- Local and remote backends share the same MCP tool surface where semantics are valid.
- WebDAV backend includes configurable transient `MOVE` retry/backoff logic with destination-state confirmation for partial-success cases.

### 9.2 Google Drive Backend
- Uses OAuth credentials and token refresh against Google OAuth token endpoint.
- Resolves target root from `folder_id` or Google Drive folder URL.
- Supports read/write/list/delete/copy/move/create-dir semantics scoped to the configured Drive folder.
- Returns deterministic not-supported for POSIX-only operations such as `chmod_path`.

## 10. Testing Architecture
- Unit tests for module correctness.
- System tests for runtime contracts.
- Integration tests for multi-module behavior over real HTTP tool calls.
- Application tests for realistic multi-step workflows.

Current baseline: full suite green (`181 passed, 15 skipped`) under smoke env; additional suites remain explicitly flag-gated (docker, remote matrix, live OAuth/live Drive, preprod).

## 11. Documentation Map
- Requirements: `docs/REQUIREMENTS.md`
- Tasks traceability: `docs/TASKS.md`
- Test traceability + run evidence: `docs/TESTS.md`
- API contract summary: `API_DOCUMENTATION.md` and `openapi.json`
