# File MCP Server - Description

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

Core component layers separate transport from domain logic. `src/file_mcp_server/*` handles lifecycle, transport wiring, middleware, and dispatch. `src/file_tools/*` provides reusable modules for config loading, scope policy, atomic IO, structured editing (JSON/YAML/XML/HTML/Markdown), sed-like transactions, search, conversion, validation, diffing, base64 operations, and audit/snapshot behavior.

Operationally, the service supports STDIO and HTTP modes (`streamable-http`, `http`, `sse`) with health/readiness endpoints. Integration and application tests verify end-to-end flows across scoped CRUD, structured edits with rollback behavior, search limits/timeouts, conversion backend selection, diff/meld optionality, base64 round-trips, lifecycle start/stop/status, and dockerized runtime behavior.
Endpoint health management performs startup checks across configured backends, applies retry/recovery policies, and can trigger deterministic restart-exit behavior for supervisors. Admin onboarding routes support Google Drive OAuth profile binding and hot config reload without process restart.

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

Transport/server logic remains thin by design, delegating behavior to reusable handlers. This supports direct library reuse in non-server contexts and keeps operational interfaces consistent across environments. End-to-end tests provide traceability from requirements to validated behaviors, including failure-path contracts such as out-of-scope denial, dry-run no-write guarantees, rollback-on-validation failure, and backend optionality handling.

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
