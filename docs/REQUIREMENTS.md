---
template-id: T-REQ
template-version: 1.1
applies-to: docs/REQUIREMENTS.md
project: file-mcp-server
doc-last-updated: 2026-06-12T16:36:44Z
doc-git-commit: 02b2e3c250769135eef5c087b4da824fa226d023
doc-git-branch: main
doc-age-policy: indefinite
doc-conformance-stamp: 2026-06-12T16:36:44Z
req-trace-version: 1.0
req-id-prefixes-used: [SV, BO, BR, FR, UC, CS, NF, R, F]
surface-coverage: [api, mcp, a2a, webui]
---

# File MCP Server — REQUIREMENTS.md
## W28A-421 Review Status
- Reviewed for external/shareable publication during W28A-421.
- Source basis: `defaults.yaml`, 1 server source files, 9 discovered routes/endpoints, and 65 MCP tools.
- Internal-only absolute paths, environment-specific hosts, and private registries have been removed from this shareable document set.

Version: 0.4 • 2026-02-19
Status: Active (Release Candidate)

## Document Structure

This document follows the structure defined in RULES.md:
- **SV** = Scope/Vision (Section 1)
- **BO** = Business Goals/Objectives (Section 2)
- **BR** = Business/Application Requirements (Section 3)
- **FR** = Project/Functional Requirements/Features (Section 4)
- **UC** = Use Cases (Section 5)
- **CS** = Cyber Security (Section 6)
- **NF** = Non-Functional Requirements (Section 7)

**Numbering Logic**: Each prefix restarts from 1.1 (e.g., SV1.1, SV1.2, BO1.1, BR1.1, FR1.1, UC1.1, CS1.1, NF1.1).

---

## 1. Scope/Vision (SV)

### SV1.1: System Overview
`file-mcp-server` provides a **language-neutral** set of filesystem and document-manipulation tools for automation and agent workflows. It exposes tools over an MCP/JSON-RPC-style boundary, **does not include LLM functionality**, and is designed for deterministic, safe file operations within a configured scope.

### SV1.2: Key Definitions
- **Profile / Configuration**: Named configuration bundle (e.g., `default`, `config1`) containing API key(s), scope, allowed file types, validation behaviour, snapshot policy, and audit log settings.
- **Scope**: Allowed root directories plus allow/deny patterns that constrain file operations.
- **Structured edit**: Format-aware operation on JSON/YAML/XML/HTML/Markdown structures.
- **Sed-like edit**: Line/range/regex-based text editing applied to textual formats.
- **Audit log**: Append-only record of tool calls and mutation attempts (successful or not), including metadata, hashes, and validation results.
- **Snapshot**: Copy/version of file contents taken before mutations, stored in a configured location.

### SV1.3: In-Scope (v1)
- Filesystem operations: read/write/move/copy/delete, list, search.
- Structured edits for JSON/YAML/XML/HTML/Markdown and sed-like edits for text.
- Validation before/after edits with strict/warn/ignore policy.
- Diff generation and optional meld integration.
- Audit logging and configurable snapshots.
- Conversion of common formats (PDF, Office) to Markdown/text (best-effort, pluggable).
- Configuration-driven scope, auth, and operational limits.
- **Simple server lifecycle management** for local testing (start/stop/status via script).

### SV1.4: Out-of-Scope (v1)
- LLM integration, prompt tooling, or content generation.
- Internet crawling/searching; only local filesystem search is supported.
- UI front-end beyond optional meld invocation.
- Distributed filesystem consistency guarantees beyond POSIX semantics.

---

## 2. Business Goals/Objectives (BO)

### BO1.1: Safe, Bounded File Operations
Provide reliable, bounded file tooling that cannot access or modify files outside configured scope.

### BO1.2: Deterministic & Auditable Changes
Ensure all mutations are deterministic, validated, and fully auditable with optional snapshots.

### BO1.3: Reusable Tooling
Enable reuse of file tools outside the server runtime (library-first design).

### BO1.4: Simple Operations
Offer simple, test-friendly server lifecycle control (start/stop/status) and configuration management.

### BO1.5: Test-Driven Delivery
Ensure REQUIREMENTS → TESTS traceability so tests validate every requirement.

---

## 3. Business/Application Requirements (BR)

### BR1.1: Language-Neutral Tooling
System shall expose file tools via a language-neutral MCP/JSON-RPC interface with stable schemas.

### BR1.2: Safe Structured Editing
System shall support structured edits with validation, snapshots, and audit logging for traceability.

### BR1.3: Comprehensive File Operations
System shall provide complete filesystem operations and search within configured scope(s).

### BR1.4: Conversion & Diff Utilities
System shall provide conversion and diff tools to support automated workflows.

### BR1.5: Configuration-Driven Security
System shall enforce authentication and scope policy using configuration precedence rules.

### BR1.6: Local Test Operations
System shall support simple server start/stop/status routines suitable for local testing.

---

## 4. Functional Requirements/Features (FR)

### FR1.1: Tool Boundary & Schema Validation
- The server SHALL expose tool discovery and execution in a language-neutral manner (JSON input/output).
- The server SHALL validate inputs and outputs against schemas.
- The server SHALL return structured errors with machine-readable codes and human-readable messages.

### FR1.2: Transport Support
- The server SHALL support STDIO transport for MCP harnesses.
- The server SHOULD support HTTP transport where configured.
- API transport plumbing SHALL integrate `cloud_dog_api_kit` (PS-20) contracts for health/readiness/liveness and error envelope standards.

### FR1.3: Configuration Precedence & Zero Hardcoding
- Configuration SHALL load via precedence: `os.environ` → env file → `config.yaml` → `defaults.yaml`.
- Configuration loading SHALL be delegated to `cloud_dog_config` (PS-80) via the project adapter.
- Logging configuration SHALL resolve from loaded profile config (via `cloud_dog_config`), not direct `os.environ` reads in `file_tools`.
- The system SHALL NOT hardcode API keys, scope roots, allowed extensions, or log paths.
- The config compiler SHALL support environment and Vault interpolation in YAML values (e.g., `${VAR}`, `${vault.*}`).

### FR1.4: Configuration Profiles
- The system SHALL support multiple named profiles, including `default` and additional profiles.
- The system SHALL allow selecting an active profile per request (or via server default).
- Per-request profile selection SHALL support:
  - query parameter `profile=<name>`
  - header `X-File-MCP-Profile: <name>`
  - fallback to server default profile when omitted/invalid
- Each profile SHALL define API keys, scope, allowed types, audit, snapshots, validation, and conversion settings.
- A single server instance SHALL support serving multiple profiles concurrently.

### FR1.5: Authentication
- The system SHALL require an API key for all tool calls.
- The system SHALL support multiple keys per profile (key rotation).
- API key validation SHALL be profile-aware; a key valid for profile `A` SHALL NOT authenticate profile `B`.
- The system SHALL NOT log raw API keys.

### FR1.6: Scope Enforcement
- Every file operation SHALL be constrained to configured scope roots.
- The system SHALL prevent directory traversal (`..`), symlink escape, and cross-root access.
- The system SHALL apply allow/deny patterns consistently for all operations.

### FR1.7: File Read Operations
- The system SHALL support reading text and binary files within scope.
- The system SHALL provide encoding detection and allow explicit encoding hints.
- The system SHALL support partial reads (byte ranges or line ranges) for large files.

### FR1.8: File Mutation Operations
- The system SHALL support writing, moving, copying, and deleting files within scope.
- Mutations SHALL use file locking and atomic writes (temp + fsync + rename).
- The system SHALL support `dry_run` for mutating tools that can compute outcomes without writing.
- The system SHALL record audit events for all mutation attempts.

### FR1.9: Search
- The system SHALL support filename/path search (glob/regex) and content search (literal/regex) with context lines.
- Search SHALL honour scope deny patterns and size limits.
- Search SHOULD support optional traversal depth and timeout controls for large trees.

### FR1.10: Base64 Encode/Decode
- The system SHALL support base64 encode/decode for strings and bytes.
- The system SHOULD support file-based base64 operations (encode/decode a file’s content).

### FR1.11: Diff Generation
- The system SHALL generate unified diffs for strings, files, and edit previews.
- The system SHOULD provide configurable context line counts.

### FR1.12: Meld Integration (Optional)
- The system SHOULD support launching `meld` when enabled, available, and supported by the environment.
- If unavailable, the tool SHALL return a non-fatal warning and not fail other operations.

### FR1.13: Structured Edits — General
- The system SHALL support structured CRUD operations for JSON, YAML, XML, HTML, and Markdown.
- Structured edit tools SHALL parse, apply deterministic changes, serialize consistently, emit preview diffs, and integrate with validation, snapshots, and audit.

### FR1.14: Structured Edits — JSON/YAML
- Addressing SHALL support JSON Pointer (`/a/b/0`) and optional dot-path (`a.b[0]`).
- Operations SHALL include add/insert, update/replace, delete, move/copy, extract, and merge.
- YAML edits SHALL preserve comments/ordering where feasible (ruamel.yaml).

### FR1.15: Structured Edits — XML/HTML
- XML addressing SHALL support XPath; HTML addressing SHALL support CSS selectors and/or XPath.
- Operations SHALL include add/update/remove attributes, add/remove nodes, replace text, and extract fragments.
- HTML parsers SHOULD tolerate malformed markup and return warnings; XML validation MUST enforce well-formedness in strict mode.

### FR1.16: Structured Edits — Markdown
- Addressing SHALL support heading path arrays and slug/anchor addressing where feasible.
- Operations SHALL include replace/insert/extract section and update YAML frontmatter (if present).

### FR1.17: Sed-like Edits (Text)
- The system SHALL support regex replace, insert before/after match, delete lines, and replace ranges.
- The system SHALL support multi-operation transactions (apply N edits atomically).

### FR1.18: Validation / Syntactical Analysis
- The system SHALL implement `validate_file` for JSON, YAML, XML, HTML, and Markdown.
- For mutations, the system SHALL support pre-validation (optional) and post-validation (configurable).
- Validation policy per type SHALL support `strict`, `warn`, and `ignore`.

### FR1.19: Audit Logging
- The system SHALL write append-only audit entries for all mutating operations and attempts.
- Audit entries SHALL include timestamp, tool name, paths, hashes, diff summary/reference, validation results, snapshot reference, and status.
- Audit/operational logging plumbing SHALL be delegated to `cloud_dog_logging` (PS-40), with structured JSONL output.
- Request-scoped log entries SHALL include correlation identifiers propagated through middleware/context.
- Sensitive fields (`token`, `secret`, `password`, `api_key`) SHALL be redacted in log output.

### FR1.20: Snapshots / Backups
- The system SHALL provide snapshot capability controlled by configuration: disabled, on-change, or scheduled (optional).
- Snapshot retention SHALL be configurable by days, count, and/or max storage size.
- Snapshot directory SHALL be inside scope or explicitly allowed by policy.

### FR1.21: Conversion Pipeline
- The system SHALL provide `convert_file` converting common formats to Markdown, text, and JSON/YAML (best-effort).
- Supported inputs SHALL include PDF and Office formats (docx/xlsx/pptx).
- Conversion backends SHALL be pluggable and discovered at runtime; external tools are optional.

### FR1.22: Server Lifecycle Control (Testing)
- The project SHALL provide a simple start/stop/status workflow for local testing.
- If a `server_control.sh` script is present, it SHALL support `start`, `stop`, `status` with a required env file flag (e.g., `--env private/env-<name>`).
- Direct process management (pkill/manual PID) SHALL NOT be required for normal testing.

### FR1.23: Health & Readiness
- The server SHOULD expose a health/readiness check (transport-appropriate) that reports status without disclosing secrets.
- Health endpoints SHALL include `/health`, `/ready`, and `/live` responses aligned to PS-20.

### FR-P001: backend_status tool
The server SHALL expose a `backend_status` MCP tool that returns the health and configuration
status of all configured storage backends (local, WebDAV, S3, Google Drive, FTP).
Reference: ARCHITECTURE.md § Storage Backend Management

### FR1.24: Tool Reuse Outside Server
- The `file_tools` library SHALL have no dependency on MCP server transport.
- All tool handlers SHALL be callable directly from Python without running the server.
- The server SHALL be a thin wrapper around the registry/handlers.

### FR1.25: POSIX Compliance
- The system SHALL operate correctly on POSIX systems and avoid non-portable filesystem behaviors.

### FR1.26: Remote Storage Backends
- The system SHALL support configurable storage backends per profile: `local`, `s3`, `webdav`, `ftp`, `google_drive`.
- The system SHALL expose the same MCP tool surface for all backends where semantics are supported.
- For capabilities that cannot be meaningfully implemented on a backend (e.g., POSIX chmod on object storage), the system SHALL return a deterministic `not supported for backend` error.

### FR1.27: Remote Backend Path Semantics
- For non-local backends, tool `path` parameters SHALL be treated as logical POSIX paths.
- Scope roots for non-local backends SHALL be evaluated as logical prefix roots (not OS filesystem paths).

### FR1.28: Remote Backend TLS Controls
- For HTTPS/TLS remote backends, the system SHALL support:
  - ignoring TLS verification errors (explicit opt-in)
  - trusting a provided CA bundle path
- Raw credentials MUST NOT be logged.

### FR1.29: Remote Backend Timeouts
- Remote backend operations SHALL honor a configurable timeout (per profile limits) to bound request duration.

### FR1.30: Endpoint Health Startup Checks
- On startup, the system SHALL probe configured storage endpoints and record per-backend status (`healthy`, `temporary_unavailable`, `busy_temporary`, `auth_failed`, `failed`).
- Startup checks SHALL support configurable retry behaviour (`max_retries`, `retry_interval_s`, `retry_window_s`).
- The server SHALL log startup endpoint status to console and operational logs.

### FR1.31: Endpoint Health Runtime Recovery
- The system SHALL support runtime recovery attempts for unhealthy backends after a configurable cooldown (`recover_after_s`).
- The system SHALL track consecutive failures and a restart-required threshold (`max_failures_before_restart`).
- Tool calls against unhealthy backends SHALL return deterministic, structured backend-unavailable errors.

### FR1.32: Google Drive OAuth and Folder Binding
- The system SHALL support Google Drive as a configured backend using OAuth credentials.
- The configuration SHALL accept either a folder id or a folder URL and resolve to the target Drive folder.
- The project SHALL provide an OAuth helper script that generates an auth URL and exchanges auth code for tokens suitable for env configuration.

### FR1.33: Restart Threshold Exit Policy
- The system SHALL support an optional restart-exit policy when endpoint health reaches restart threshold.
- When enabled, the server SHALL exit with a configurable non-zero exit code to allow container/supervisor restart policies.

### FR1.34: Admin Config Hot Reload
- The system SHALL expose an admin reload operation to rebind the active profile tool registry without process restart.
- Admin routes SHALL be gated behind explicit enablement and optional token auth.
- Successful Google Drive OAuth callback SHOULD auto-apply the updated profile when configured.

### FR1.35: WebDAV Transient MOVE Resilience
- The system SHALL support configurable retry handling for transient WebDAV `MOVE` failures.
- Retry controls SHALL be configuration-driven (retry count, backoff, probe timeout, and retriable status list).
- If a transient `MOVE` response occurs but destination state confirms operation already applied, the system SHALL treat it as successful.

### FR1.36: Single-Server Multi-Profile Routing
- One server process SHALL host multiple profiles concurrently and route each tool call to the selected profile context.
- Profile selection SHALL support request query/header selectors with deterministic fallback to server default profile.
- Profile routing SHALL enforce profile-local controls (API keys, scope roots, allow/deny patterns, allowed extensions, read-only extensions, limits).

### FR1.37: Web UI Route Contract (`UI-P5-FILE-REQ`)
- The monorepo frontend app `@cloud-dog/app-file-mcp` SHALL expose the following routes:
  - `/login`
  - `/dashboard`
  - `/file-browser`
  - `/search`
  - `/storage-profiles`
  - `/audit-log`
  - `/settings`
- The default route (`/`) SHALL redirect to `/dashboard` for authenticated users.
- Unknown routes SHALL redirect to `/dashboard`.

### FR1.38: Web UI Runtime Config Contract (`UI-P5-FILE-REQ`)
- The frontend runtime config object (`window.__RUNTIME_CONFIG__`) SHALL provide:
  - `ENV`
  - `API_BASE_URL`
  - `AUTH_MODE`
  - `AUDIT_LOG_PATH`
  - `DEFAULT_BROWSE_PATH`
  - `PROFILE_STORE_PATH`
- Runtime config SHALL be loaded from `apps/file-mcp/public/runtime-config.js` (or equivalent deployment artefact), not hardcoded in React components.

### FR1.39: Web UI Authentication Expectations (`UI-P5-FILE-REQ`)
- UI auth mode SHALL support API-key login for file-mcp.
- Login SHALL validate the key against a real backend call before marking the session authenticated.
- Any 401/403 from backend API calls SHALL force session logout and return to sign-in state.
- The UI SHALL not display fake success state when auth fails.

### FR1.40: Web UI API Contract Expectations (`UI-P5-FILE-REQ`)
- The UI SHALL call live backend endpoints via `API_BASE_URL` and SHALL not use mocked API responses in E2E/a11y validation.
- UI flows SHALL depend on real `file-mcp-server` tool contracts for:
  - health/status (`/health`)
  - tools list and backend status
  - filesystem CRUD and directory listing
  - search paths/content
  - audit log read/export
  - storage profile load/save
- Backend failures SHALL be surfaced as user-visible error messages (`role="alert"` or equivalent status copy).

### FR1.41: Dashboard Flow (`UI-P5-FILE-REQ`)
- Dashboard SHALL display service status, active backend, backend count, and available tool count.
- Dashboard quick actions SHALL route to file browser, search, storage profiles, and audit log.
- Dashboard SHALL show recent audit activity when audit data is available.

### FR1.42: File Browser and Search Flow (`UI-P5-FILE-REQ`)
- File browser SHALL support browse/open/read/write/delete/copy/move and create directory/file actions.
- Search SHALL support filename search, content search, and regex/grep mode.
- Search results SHALL allow opening the selected result in file browser context.

### FR1.43: Profiles, Audit, and Settings Flow (`UI-P5-FILE-REQ`)
- Storage profiles page SHALL support create/edit/delete/test-connection workflows.
- Audit log page SHALL support refresh, filtering (action/outcome/path/date), pagination, and CSV export.
- Settings page SHALL expose runtime paths and an explicit health-check action.

### FR1.44: Web UI Accessibility (`UI-P5-FILE-REQ`)
- Core pages SHALL meet WCAG 2.1 AA baseline checks in automated a11y test runs.
- Key status/error surfaces SHALL use semantic roles (`status`, `alert`) for assistive technology compatibility.
- Interactive controls SHALL have accessible names suitable for role-based test selectors.

### FR1.45: Web UI Failure and Timeout Behaviour (`UI-P5-FILE-REQ`)
- On backend timeout/unavailable/error conditions, UI SHALL show explicit failure state and SHALL NOT silently report success.
- Loading states SHALL be visible while requests are in flight.
- E2E/a11y validation for closeout SHALL run against a real backend runtime (no degraded fallback mode).

### FR1.46: A2A Health Auth Contract
- The server SHALL expose `GET /a2a/health` in local-server and local-docker runtime modes.
- `GET /a2a/health` without valid auth SHALL return `401`.
- `GET /a2a/health` with `Authorisation: Bearer 12345678` SHALL return `200` in strict local test mode.
- A2A auth verification SHALL use the same API-key authority as MCP/API auth verification (no separate A2A key store).

### FR1.47: Web UI Standards Merge (W28A-896)
- [EXISTING] The frontend app `@cloud-dog/app-file-mcp` SHALL provide the routeable WebUI surfaces `/`, `/login`, `/file-browser`, `/search`, `/storage-profiles`, `/audit-log`, `/settings`, `/admin/users`, `/admin/groups`, `/admin/api-keys`, `/admin/rbac`, `/google-drive-settings`, `/jobs`, `/mcp-console`, `/a2a-console`, `/api-docs`, and `/about`.
- [EXISTING] `/dashboard` SHALL redirect to `/`, `/admin-identity` SHALL redirect to `/admin/identity`, `/admin/identity` SHALL redirect to `/admin/users`, and unknown routes SHALL redirect to `/`.
- [EXISTING] The app code SHALL retain the 16 primary page/view implementations used by the service: `DashboardPage`, `FileBrowserPage`, `SearchPage`, `StorageProfilesPage`, `AuditLogPage`, `SettingsPage`, `AdminIdentityPage`, `AdminUsersPage`, `AdminGroupsPage`, `AdminApiKeysPage`, `AdminRbacPage`, `GoogleDriveSettingsPage`, `JobsPage`, `McpConsolePage`, `A2aConsolePage`, and `ApiDocsPage`.
- [NEW] `DashboardPage` SHALL align to PS-77 dashboard requirements: `/` as the CW-M1 landing page, `DashboardLayout`/shell structure, `ServiceStatusBar`, health widgets, metric cards, quick actions, recent-activity list, and no raw JSON on the dashboard surface.
- [EXISTING] `FileBrowserPage` SHALL remain the primary tree/workspace surface for scoped file operations with navigation, upload/download, CRUD actions, selection, and an entries `DataTable`.
- [NEW] `FileBrowserPage` SHALL align to the PS-77 Tree/workspace family and adopt governed tree/upload/editor surfaces where available, including PS-84 shared code/config viewers or editors for file-content and diff-centric interactions instead of raw bespoke text areas.
- [EXISTING] `SearchPage` SHALL support filename, content, and regex/grep search and allow operators to open a selected result in file-browser context.
- [NEW] `SearchPage` SHALL align to the SearchPanel standard: use `SearchPanel` with declarative filters, visible loading state, `Enter` execution, `Escape` clear behaviour, and governed results presentation.
- [EXISTING] `StorageProfilesPage` SHALL provide profile list/create/edit/delete/test-connection workflows through `DataTable` and `EntityDialog`.
- [NEW] `StorageProfilesPage` SHALL be treated as a PS-77 List/detail administrative surface with sortable columns, pagination, multi-select, bulk actions, and standard page-header action placement.
- [EXISTING] `AuditLogPage` SHALL provide log refresh, filtering, pagination, export, and `DataTable`-based inspection of live audit entries.
- [NEW] `AuditLogPage` SHALL remain a PS-77 List/detail operational page with governed filter, empty, loading, and export states and without bespoke tabular markup.
- [EXISTING] `SettingsPage` SHALL expose service info, server/runtime paths, storage/backend, logging, service-specific config, and health status.
- [NEW] `SettingsPage` SHALL align to PS-73, PS-81, and PS-84: nested config inspection SHALL use `JsonExplorer`, editable JSON/YAML surfaces SHALL use `CodeEditor`, secrets SHALL remain masked in inspect/edit/export modes, and `JsonBlock` SHALL be limited to simple shallow payloads.
- [EXISTING] `AdminIdentityPage` SHALL remain the shared implementation surface behind the Users, Groups, and API Keys route pages.
- [NEW] `AdminIdentityPage` SHALL only be used as an implementation helper; route-level admin pages SHALL remain one-entity-per-page in line with PS-77 CW-L1.
- [EXISTING] `AdminUsersPage` SHALL provide a routed Users management surface backed by `DataTable` and `EntityDialog`.
- [NEW] `AdminUsersPage` SHALL align to PS-71 Users requirements: required user columns, create/edit/disable/delete flows, bulk delete, status badges, and RBAC-aware action visibility.
- [EXISTING] `AdminGroupsPage` SHALL provide a routed Groups management surface backed by `DataTable` and `EntityDialog`.
- [NEW] `AdminGroupsPage` SHALL align to PS-71 Groups requirements: required columns, create/edit/delete flows, member-management workflow, bulk delete, role/status display, and RBAC-aware action visibility.
- [EXISTING] `AdminApiKeysPage` SHALL provide a routed API Keys management surface backed by `DataTable` and `EntityDialog`.
- [NEW] `AdminApiKeysPage` SHALL align to PS-71 API Key requirements: owner/scopes/status/expiry columns, create flow with one-time raw-key reveal and copy action, revoke/bulk-revoke workflows, and RBAC-aware action visibility.
- [EXISTING] `AdminRbacPage` SHALL provide a routed RBAC inspection surface using the shared `@cloud-dog/ui` RBAC page pattern.
- [NEW] `AdminRbacPage` SHALL align to PS-71 RBAC requirements: role definitions, user-role bindings, group-role bindings, effective-permissions inspection, and real bind/unbind actions where the backend exposes them.
- [EXISTING] `GoogleDriveSettingsPage` SHALL provide the Google Drive OAuth/profile binding workflow for file-mcp storage profiles.
- [NEW] `GoogleDriveSettingsPage` SHALL follow PS-77 viewer/editor layout requirements with governed page header, cards, status/error states, and service-specific configuration actions documented in this service requirements set.
- [EXISTING] `JobsPage` SHALL provide a routed jobs surface with summary metrics, filters, `DataTable`, detail dialog, and job state actions backed by live service data.
- [NEW] `JobsPage` SHALL continue to align to PS-76 column order, status mapping, row actions, bulk actions, metrics bar, detail dialog sections, and RBAC-aware behaviour.
- [EXISTING] `McpConsolePage` SHALL use the shared `McpConsole` pattern against the live tool set and live execution endpoint.
- [NEW] `McpConsolePage` SHALL align to PS-72 console requirements including auth-status display, schema-driven parameter templates, JSON response display, execution history, and governed loading/error states.
- [EXISTING] `A2aConsolePage` SHALL use the shared `A2aConsole` pattern against the live A2A endpoint.
- [NEW] `A2aConsolePage` SHALL align to PS-72 console requirements including auth-status display, task submission/status tracking, agent-card-linked context, and governed loading/error states.
- [EXISTING] `ApiDocsPage` SHALL expose API, MCP, and A2A documentation through `ApiDocsPanel`, tabs, reference tables, and inline rendered documentation.
- [NEW] `ApiDocsPage` SHALL align to PS-74: API tab first, live MCP tool reference via `DataTable`, live A2A skill reference from the agent card where available, inline document rendering, and project documentation sourced from real service docs where available.

---

## 5. Use Cases (UC)

### UC1.1: Read File Within Scope
Client reads a file within scope and receives content plus metadata.

### UC1.2: Structured Edit With Validation
Client applies a structured JSON/YAML/XML/HTML/Markdown edit, system validates, snapshots, and audits the mutation.

### UC1.3: Search Content Across Tree
Client searches content or filenames across scoped roots and receives matches with context.

### UC1.4: Convert Document to Markdown
Client converts PDF/DOCX to Markdown or text and receives validated output with warnings if needed.

### UC1.5: Preview Diff (Dry-Run)
Client performs a dry-run edit to obtain a preview diff without modifying files.

### UC1.6: Inspect Audit or Snapshots
Operator lists snapshot history or audit trail to trace changes.

### UC1.7: Start/Stop Server for Local Testing
Operator uses the approved script or command to start/stop/status the server using an env file.

### UC1.8: Remote Storage Safe Edit Workflow
Client performs the safe edit workflow (read -> diff -> edit -> validate -> audit) against a configured remote backend within scope and limits.

### UC1.9: Remote Storage Search Workflow
Client searches filenames and content across a remote backend root with depth/timeout/result limits enforced.

### UC1.10: Startup Health and Degraded Endpoint Handling
Operator starts the server, receives endpoint health status, and the system reports retry/recovery/failure states consistently to logs and tool callers.

### UC1.11: Google Drive Managed File Workflow
Client performs scoped file operations against a configured Google Drive folder using OAuth-managed credentials.

### UC1.12: Restart on Endpoint Degradation
Operator enables restart-threshold policy and the server exits deterministically when endpoint failure thresholds are reached.

### UC1.13: Remote OAuth Bind Without Restart
Operator binds Google Drive to a profile through admin pages and the server applies the updated profile configuration immediately.

### UC1.14: Multi-Profile Single-Server Routing
Operator runs one server instance with multiple profiles loaded. Clients select profile per request via query/header and receive profile-specific auth, scope, and type-policy enforcement.

---

## 6. Cyber Security (CS)

### CS1.1: Authentication
All tool calls SHALL require API key authentication; raw keys SHALL NOT be logged.

### CS1.2: Scope Enforcement
The system SHALL prevent traversal, symlink escape, and cross-root access.

### CS1.3: Secret Handling
Credentials SHALL be provided via env files or environment variables and SHALL NOT be committed.

### CS1.4: Audit Integrity
Audit logs SHALL be append-only with restricted access; direct edits are forbidden.

### CS1.5: Resource Limits
The system SHALL enforce size, timeouts, and conversion limits to reduce abuse or denial-of-service risks.

---

## 7. Non-Functional Requirements (NF)

### NF1.1: Reliability & Integrity
Mutations SHALL be atomic, recoverable via snapshots (when enabled), and never leave partial files.

### NF1.2: Performance
Search and conversion SHALL enforce configurable limits; large file reads SHOULD support streaming/ranges.

### NF1.3: Observability
Operational logs SHALL be separate from audit logs; log levels and destinations are configurable.

### NF1.4: Determinism
Structured edits SHALL produce deterministic output for identical inputs and config.

### NF1.5: Portability
System SHOULD run on Linux/macOS; Windows support is optional.

### NF1.6: Operational Controls
Server lifecycle control SHALL be test-friendly and config-driven; no manual process management required.

### NF1.7: Configuration Compliance
All configuration must follow the precedence chain with zero hardcoded values.

### NF1.8: Test-Driven Delivery
Every requirement SHALL map to at least one test in `docs/TESTS.md`. Tests validate success paths, failure paths, and edge cases, and must use real filesystem operations.

---

## 8. Acceptance Criteria (examples)

1. **Scope safety**: Attempting to read `../outside.txt` MUST fail even with a valid API key.
2. **Strict validation**: Editing JSON into invalid JSON MUST fail and MUST not modify the original file.
3. **Warn validation**: Editing malformed HTML in warn mode MUST succeed but return warnings.
4. **Audit completeness**: Every successful write MUST produce an audit entry with hashes and validation outcome (if enabled).
5. **Snapshot restore**: With snapshots enabled, a pre-mutation snapshot MUST exist after a mutation.
6. **No hardcoded config**: Changing audit log path in config MUST redirect logs without code changes.
7. **Server/tool separation**: Tools package MUST be importable and usable without running the server.

---

## 9. Out of Scope (Explicit)

- LLM integration or prompt tooling
- Internet search/crawling (local filesystem only)
- UI front-end beyond optional meld invocation
- Distributed filesystem consistency guarantees beyond POSIX semantics

### Database Abstraction (cloud_dog_db adoption)

- R-DB-01: All database access MUST use `cloud_dog_db` engine/session/CRUD abstractions
- R-DB-02: Engine creation MUST use `cloud_dog_db` engine factories
- R-DB-03: Session management MUST use `cloud_dog_db.session.SyncSessionManager`/`AsyncSessionManager`
- R-DB-04: Schema migrations MUST use `cloud_dog_db` migration runner
- R-DB-05: Direct sqlite3/create_engine()/sessionmaker()/raw Session() FORBIDDEN in app code
- R-DB-06: DB health MUST use `cloud_dog_db.health.probe_database()`
- R-DB-07: DB connection config MUST come from cloud_dog_config/Vault-backed env hierarchy

## Configuration CRUD Requirements (CFG)

Profile concept for this project: file storage profiles defining scope roots, storage backend settings, auth policy, limits, validation behaviour, snapshots, and audit paths.

| ID | Requirement |
|----|-------------|
| CFG-01 | The system SHALL support creating a new file profile via the API with all profile settings that would otherwise be available via environment variables or env-file configuration. |
| CFG-02 | The system SHALL support reading file profiles via the API, including both list and detail retrieval. |
| CFG-03 | The system SHALL support updating an existing file profile via the API. |
| CFG-04 | The system SHALL support deleting a file profile via the API. |
| CFG-05 | File profile CRUD operations SHALL be available as MCP tools with equivalent functionality. |
| CFG-06 | File profile change events SHALL be broadcast via the A2A interface per **PS-72 §A2A-change-events** (canonical envelope `{type, topic, timestamp, payload}`; reference implementation `cloud_dog_api_kit.a2a.events` ≥0.11.0; see platform-standards `docs/standards/PS-72-agent-to-agent.md`). |
| CFG-07 | File profile CRUD operations SHALL be available in the WebUI with RBAC enforcement. |
| CFG-08 | The system SHALL support creating, reading, updating, and deleting users via the API. |
| CFG-09 | The system SHALL support creating, reading, updating, and deleting groups with role assignments via the API. |
| CFG-10 | The system SHALL support creating, listing, and revoking API keys with per-key capability scoping via the API. |
| CFG-11 | User, group, and API-key management SHALL be available via MCP, A2A, and WebUI with RBAC. |
| CFG-12 | All CRUD operations SHALL be audit logged with user identity, action, timestamp, and outcome. |
| CFG-13 | Only admin users SHALL be able to create, update, and delete file profiles and manage users or groups; read-only access SHALL be available to authorised non-admin users. |


## W28A-883 PS-78 Cross-Platform File Handling Addendum

### Verified current state

- `file-mcp` is the strongest existing PS-78 reference for storage backends: local, S3, FTP, WebDAV, and Google Drive via `cloud_dog_storage`.
- MCP already exposes `file_upload`, `file_download`, and base64-oriented file transfer tools.
- The WebUI `FileBrowserPage` already supports file upload and download with a standard file input, plus storage-profile administration.

### Required additions to satisfy PS-78

- Add a standard REST file lifecycle contract so the service also exposes `/files/upload`, `/files/upload_base64`, `/files`, `/files/{id}`, `DELETE /files/{id}`, and `/files/{id}/download`.
- Add A2A file transfer skills or task payloads for cross-agent use of file-mcp.
- Define the delegated chat contract explicitly for services such as chat-client that depend on file-mcp for storage and file transfer.
- Add URI-source intake coverage for `http://`, `https://`, `s3://`, `ftp://`, and `file://` where policy allows.

### Required PS-78 test plan

- API: upload, list, metadata, download, delete across backend types.
- MCP: base64 upload/download, path-based file flows, and URI-source handling.
- A2A: file transfer between agents using file-mcp as the file surface.
- WebUI: upload, download, browse, delete, profile/backend switching.
- Delegated chat integration: verify chat-client can upload to and download from file-mcp through the standard contract.

## PS-40 / W28A-619 Logging and Audit Requirements

The service MUST use `cloud_dog_logging` as the only application and audit logging implementation. Raw stdlib logging setup, direct `logging.getLogger()` calls, bespoke audit emitters, and print-based operational logging are not compliant except inside the platform logging package itself.

Every auditable event MUST emit a PS-40/NIST AU-3 audit record with: `event_type`, `action`, `timestamp`, `service`, `component`, `service_instance`, `environment`, `source_host`, `source_process`, `source_application`, `source_address` where available, `destination_address` where available, `outcome`, actor identity including user/service/system plus account/process/device identifiers where available, `target`, `process_id`, `affected_files` where relevant, `correlation_id`, `trace_id`, and `request_id`.

Auditable events MUST include authentication and authorisation decisions, user/group/API-key/RBAC changes, storage profile/file/folder/share operations, MCP/A2A/API calls, job lifecycle changes, configuration changes, data access and mutation, denials, failures, and privileged operations. Secrets MUST be redacted before persistence. Tests MUST cover schema fields, event coverage, redaction, append-only audit persistence, retention/integrity, and WebUI observability rendering/filtering.

## 5. Cyber Security & Negative Flows

Mandatory schema per PS-REQ-TEST-TRACE v1.0 §3.4. Every project covers anon-denied, wrong-role-denied, missing-param-error per declared surface. The CS rows below are platform-baseline; project-specific extensions append in §5.1.

| ID | Threat / negative scenario | Surface | Role(s) attempted | Expected | Tests |
|---|---|---|---|---|---|
| `CS-001` | Anon attempts data read | `api`, `mcp`, `a2a`, `webui` | `anon` | `401` | (to be bound in Instruction 4 by operator) |
| `CS-002` | read-only attempts write | `api`, `mcp` | `read-only` | `403` | (to be bound in Instruction 4 by operator) |
| `CS-003` | Missing required param | `api` | `admin` | `422` | (to be bound in Instruction 4 by operator) |
| `CS-004` | Wrong-role privileged op | `mcp` | `read-write` | `403` | (to be bound in Instruction 4 by operator) |



<!-- W28C-1710a recovery: full content from archive/2026-06-12/DESCRIPTION.md (archived sha256=1072f02d490d, 92 lines) -->

## Recovered domain content — `archive/2026-06-12/DESCRIPTION.md` (92 lines)

_This section carries forward the full content of the archived predecessor doc verbatim. Topic checklist + SHA256 chain in `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/file-mcp-server/DESCRIPTION.md.topics.tsv`. Archive contents are unchanged (sha256 stable)._

# File MCP Server - Description
Release Status: Release Candidate (2026-02-12)

## Overview (50 words)
file-mcp-server is a language-neutral MCP service for deterministic file operations within configured scope boundaries. It delivers secure read/write/search/edit/conversion tools, structured document manipulation, validation, snapshots, and append-only audit trails. Profiles, API-key authentication, and transport options enable reliable automation across local runtimes, containers, and test-driven operational workflows for engineering and compliance needs.

## Features and Benefits

| Feature | Benefit |
|---|---|
| Scoped filesystem access policy | Prevents out-of-scope reads, writes, and traversal |
| API-key authentication per profile | Controls tool access and supports key rotation |
| Deterministic structured edits | Produces predictable, repeatable document updates |
| Dry-run mutation previews | Reduces risk before applying file changes |
| Validation policies by file type | Enforces quality using strict, warn, ignore modes |
| Append-only audit events | Supports traceability, forensics, and compliance reporting |
| Snapshot creation and retention | Enables rollback and recovery after failed changes |
| Multi-transport MCP interface | Integrates with STDIO, HTTP, streamable HTTP, SSE |
| Conversion pipeline backends | Converts PDF and Office formats to automation outputs |
| Reusable file_tools library | Embeds core capabilities outside server runtime |

## Product Overview
file-mcp-server solves a common automation problem: safely changing files at scale without uncontrolled access, hidden side effects, or weak traceability. Traditional scripts can bypass boundaries, produce inconsistent edits, or leave poor audit evidence. This server provides a bounded, deterministic interface where every operation is validated against configuration and scope policy.

It helps by combining scoped file operations, structured document edits, transactional text updates, search, diffing, validation, conversion, snapshots, and audit logging in one language-neutral MCP service. Teams can run the same capabilities over STDIO for harnesses or HTTP-based transports for service integrations, while keeping configuration and secrets outside code.
It now also supports multi-backend execution across local, WebDAV, FTP, S3, and Google Drive targets with a consistent MCP tool contract and deterministic backend-specific unsupported errors.

It helps wherever automated file workflows are required: local engineering workspaces, CI runners, containerized integration environments, and controlled operational hosts. It helps with release-note updates, config refactoring, content normalization, search-and-fix cycles, and compliance-sensitive change tracking.

It helps developers, platform teams, QA/integration engineers, and operators who need reliable file automation with clear controls. Business stakeholders benefit from faster, safer content and configuration changes, and security/compliance stakeholders benefit from auditable mutation records and enforceable boundaries.

## Technical Capabilities
The technical process follows a deterministic runtime flow: load configuration by precedence (`os.environ` -> env file(s) -> `config.yaml` -> `defaults.yaml`), select profile, authenticate request, enforce scope/allow-deny rules, execute tool handler, then return structured output or error. Mutating operations add optional snapshot, validation checks, and append-only audit entries.

Core component layers separate transport from domain logic. `src/file_mcp_server/*` handles lifecycle, transport wiring, middleware, and dispatch. `src/file_tools/*` provides reusable modules for config loading, scope policy, atomic IO, structured editing (JSON/YAML/XML/HTML/Markdown), sed-like transactions, search, conversion, validation, diffing, base64 operations, and audit/snapshot behaviour.

Operationally, the service supports STDIO and HTTP modes (`streamable-http`, `http`, `sse`) with health/readiness endpoints. Integration and application tests verify end-to-end flows across scoped CRUD, structured edits with rollback behaviour, search limits/timeouts, conversion backend selection, diff/meld optionality, base64 round-trips, lifecycle start/stop/status, and dockerized runtime behaviour.
Endpoint health management performs startup checks across configured backends, applies retry/recovery policies, and can trigger deterministic restart-exit behaviour for supervisors. Admin onboarding routes support Google Drive OAuth profile binding and hot config reload without process restart.

Recent tested runtime capabilities also include filesystem path tools (`create_dir`, `chmod_path`, `rename_path`, `move_path`) and extended observability/audit metadata (`session_id`, `client_ip`, `duration_ms`, `params`, `outcome`) asserted in Docker integration tests.

## Where it Fits
file-mcp-server fits as a secure automation layer between agent/orchestration systems and local or mounted filesystems. It complements CI/CD pipelines, developer assistants, configuration management processes, and documentation/content pipelines by standardizing file operations through one governed API.

It aligns with services that require deterministic change execution but not model inference. It can be paired with planning/orchestration products, code-quality tooling, and compliance systems: upstream systems decide what to change, while file-mcp-server performs bounded execution, validation, and audit evidence generation.

In business terms, it reduces operational risk and manual effort for repetitive file change tasks. In solution terms, it provides a reusable control plane for file mutations with clear policy, observability, and transport flexibility.

## ARCHITECTURE
Deployment is typically single-service, stateless-at-transport, with state persisted in configured filesystem paths (workspace files, audit JSONL logs, snapshot directories). It runs natively via Python CLI or in containers, with environment-driven profile selection and health endpoints for runtime checks.

Infrastructure components include scoped root mounts, env/config files, operational logs, audit logs, and snapshot storage. Container deployments commonly mount workspace and logs as host volumes and optionally inject enterprise CA bundles. Lifecycle operations are handled by CLI commands or `server_control.sh` using explicit env files.
For remote storage robustness, WebDAV move operations include configurable retry/backoff/probe controls to handle transient 5xx/lock/timeout conditions while preserving deterministic error semantics.

Scaling is achieved by adding isolated instances per workspace, tenant, or environment profile. Because file operations are scope-bound and filesystem-centric, horizontal scaling works best when each instance has clear storage boundaries or coordinated shared storage policy. Security posture is enforced through API-key auth, root-bound checks, allow/deny patterns, extension constraints, and append-only audit design.

## Technical Design
The design meets business goals by enforcing bounded operations (BO1.1), deterministic auditable mutations (BO1.2), reusable tooling (BO1.3), and test-friendly operations (BO1.4/BO1.5). It satisfies non-functional requirements through atomic writes and locking for integrity, deterministic structured serializers, configurable timeouts/limits for performance control, and separate operational versus audit logging for observability.

Security design combines request authentication, strict scope normalization, symlink/traversal escape prevention, and deny-list enforcement before file access. Secrets are provided through env files/environment variables rather than code. Validation policy (`strict`, `warn`, `ignore`) allows controlled balance between hard enforcement and operational continuity, while audit records preserve tool, timing, path, and result metadata for forensic traceability.

Transport/server logic remains thin by design, delegating behaviour to reusable handlers. This supports direct library reuse in non-server contexts and keeps operational interfaces consistent across environments. End-to-end tests provide traceability from requirements to validated behaviors, including failure-path contracts such as out-of-scope denial, dry-run no-write guarantees, rollback-on-validation failure, and backend optionality handling.

## Key Capabilities
Scoped file CRUD and path management allow safe create/read/update/delete, move/rename, directory creation, and permission changes inside approved roots. Scenario: an integration worker stages release artifacts, renames folders, and applies permission adjustments without escaping policy boundaries.

Structured document editing supports JSON/YAML/XML/HTML/Markdown CRUD-style changes with deterministic serialization and optional validation. Scenario: a deployment pipeline updates environment manifests and release notes sections while preserving schema correctness and generating audit evidence.

Transactional sed-like text editing supports multi-operation atomic updates with rollback on failure. Scenario: a maintenance workflow replaces deprecated settings across files and guarantees either all replacements succeed or none persist.

Search and diff tooling provides path/content search with context, bounds, and unified diff generation for previews and verification. Scenario: an operator locates all TODO markers, applies edits, and confirms exact change hunks before approval.

Validation, snapshots, and audit logging provide quality gates and traceability for all mutation attempts. Scenario: a compliance-required change records pre-change snapshots, validation outcomes, and append-only audit events for post-change review.

Conversion and base64 utilities support document ingestion and binary-safe transfer in automated flows. Scenario: a team converts source documents to Markdown for downstream editing and uses base64 file operations for interoperable transport payloads.

## Example Use Cases
1. CI release documentation pipeline: convert source docs to Markdown, apply structured section edits, diff against baseline, and archive audit/snapshot evidence.
2. Secure config refactor service: search scoped repositories, run transactional text edits, validate JSON/YAML outputs, and reject out-of-scope requests.
3. Multi-tenant file automation gateway: run profile-isolated instances with per-tenant keys, roots, deny rules, and separate audit streams.
4. Operations lifecycle checks: start service with environment file, verify `/health`, execute authenticated tool calls, then stop and collect logs.
5. Compliance evidence workflow: perform approved mutations only, then export append-only audit records with session/client metadata.
6. Containerized integration harness: execute HTTP tool stories over mounted workspace/log volumes and validate deterministic results in tests.
7. Documentation modernization flow: ingest legacy documents, convert formats, update headings/frontmatter, and preserve rollback snapshots.
8. Policy-bound file maintenance: create directories, rename/move files, adjust permissions, and enforce extension/allow-deny constraints.

## Deployment
Deployment patterns include native Python process and Docker container runtime. Native mode uses `python -m file_mcp_server` or `server_control.sh` with explicit env files. Container mode mounts workspace/log directories, injects env/config paths, and exposes health and MCP endpoints over host networking or published ports.

Storage is filesystem-based: scoped workspace data, operational logs, append-only audit JSONL files, and snapshot directories with retention controls (`days`, `count`, `max_storage_mb`). There is no mandatory database dependency; persistence is achieved through mounted filesystems.

Configuration supports layered env files (including comma-separated `FILE_MCP_ENV_PATH`), runtime overrides, and profile selection. Enterprise deployments can mount CA bundles for outbound trust chains. Deployment topologies include single-instance local testing, CI integration workers, and horizontally replicated environment-specific instances with isolated scopes and log paths.
