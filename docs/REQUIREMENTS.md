# File MCP Server — REQUIREMENTS.md
Version: 0.2 • 2026-02-05
Status: Draft (expanded)

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

### FR1.3: Configuration Precedence & Zero Hardcoding
- Configuration SHALL load via precedence: `os.environ` → env file → `config.yaml` → `defaults.yaml`.
- The system SHALL NOT hardcode API keys, scope roots, allowed extensions, or log paths.
- The loader SHALL support environment-variable interpolation in YAML values (e.g., `${VAR}`).

### FR1.4: Configuration Profiles
- The system SHALL support multiple named profiles, including `default` and additional profiles.
- The system SHALL allow selecting an active profile per request (or via server default).
- Each profile SHALL define API keys, scope, allowed types, audit, snapshots, validation, and conversion settings.

### FR1.5: Authentication
- The system SHALL require an API key for all tool calls.
- The system SHALL support multiple keys per profile (key rotation).
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
- Audit output format SHOULD be JSONL for easy ingestion.

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

### FR1.24: Tool Reuse Outside Server
- The `file_tools` library SHALL have no dependency on MCP server transport.
- All tool handlers SHALL be callable directly from Python without running the server.
- The server SHALL be a thin wrapper around the registry/handlers.

### FR1.25: POSIX Compliance
- The system SHALL operate correctly on POSIX systems and avoid non-portable filesystem behaviors.

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
