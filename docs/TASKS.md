# File MCP Server — TASKS.md
Version: 0.1 • 2026-02-05
Status: Draft

## Purpose
This document provides the implementation plan for `file-mcp-server`, aligned to:
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TESTS.md`
- `RULES.md` (100% compliance)

Every requirement MUST map to at least one task and at least one test.

---

## Delivery Plan (Phased)

### Phase 1 — Foundations
- Repository structure & configuration baseline
- Configuration loader and schema
- Authentication and scope enforcement

### Phase 2 — Core File Tools
- Filesystem operations, search, diff, base64
- Structured edits and validation
- Audit logging and snapshots

### Phase 3 — Server Runtime
- Tool registry and schemas
- MCP transports (stdio, optional HTTP)
- Health/readiness and lifecycle control

### Phase 4 — Conversion & Hardening
- Conversion pipeline and backends
- POSIX portability checks
- Observability and limits

### Phase 5 — Tests & Documentation
- Implement full UT/ST/IT/AT suite
- Update documentation and cross-references

---

## Task List

### T1: Repository Structure & Baseline Docs
**Description:** Ensure repository layout matches rules, add missing doc scaffolding, and align folder readmes.
**Requirements:** SV1.1, SV1.3, BO1.4, NF1.6, NF1.7
**Architecture:** 2. Repository Layout
**Tests:** ST1.1
**Dependencies:** None
**Status:** Completed (repo layout aligned to RULES baseline and core documentation set maintained)

### T2: Configuration Loader & Precedence Chain
**Description:** Implement configuration loader and schema validation with precedence chain and profile support.
**Requirements:** FR1.3, FR1.4, CS1.3, NF1.7
**Architecture:** 3. Configuration and Precedence
**Tests:** UT1.1
**Dependencies:** T1
**Status:** Completed (bootstrap loader/models + defaults.yaml added)

### T3: Authentication & Key Rotation
**Description:** Implement API key authentication and logging redaction.
**Requirements:** FR1.5, CS1.1
**Architecture:** 4.1 Authentication
**Tests:** UT1.2, ST1.2
**Dependencies:** T2
**Status:** Completed (API key auth scaffold + unit tests added)

### T4: Scope Policy Enforcement
**Description:** Implement scope policy with allow/deny globs, traversal prevention, and read-only types.
**Requirements:** FR1.6, CS1.2
**Architecture:** 4.2 Authorisation via Scope Policy
**Tests:** UT1.3, IT1.2
**Dependencies:** T2
**Status:** Completed (core checks + unit tests scaffolded; out-of-scope mutating attempts now audited as error events in server flows)

### T5: Filesystem Operations (Read/Write/Move/Copy/Delete)
**Description:** Implement safe filesystem operations with locking and atomic writes.
**Requirements:** FR1.7, FR1.8, NF1.1
**Architecture:** 6.1 Core file operations, 4.3 Safe Writes
**Tests:** UT1.4, IT1.2
**Dependencies:** T4
**Status:** Completed (filesystem scaffold + unit tests added)

### T6: Search Tools
**Description:** Implement filename/path and content search within scope with size limits.
**Requirements:** FR1.9, NF1.2
**Architecture:** 6.2 Search
**Tests:** UT1.5, IT1.4
**Dependencies:** T4
**Status:** Completed (search utilities + unit tests added; HTTP IT1.4 coverage now verifies deny-glob enforcement, regex path search, size limits, and max-results behavior)

### T7: Base64 Utilities
**Description:** Implement base64 encode/decode helpers and optional file-based operations.
**Requirements:** FR1.10
**Architecture:** 6.3 Base64
**Tests:** UT1.6, IT1.7
**Dependencies:** T5
**Status:** Completed (base64 helpers + unit tests added; HTTP file encode/decode integration coverage added)

### T8: Diff & Meld Integration
**Description:** Implement diff generation and optional meld integration.
**Requirements:** FR1.11, FR1.12
**Architecture:** 6.4 Diff and Meld
**Tests:** UT1.7, UT1.8, IT1.5
**Dependencies:** T5
**Status:** Completed (diff/meld helpers + unit tests added; HTTP `diff_files` plus `meld_files` optional-warning integration coverage added)

### T9: Structured Edit Engines (JSON/YAML/XML/HTML/Markdown)
**Description:** Implement structured edit handlers for supported formats.
**Requirements:** FR1.13, FR1.14, FR1.15, FR1.16
**Architecture:** 6.5 Structured edits
**Tests:** UT1.9, UT1.10, UT1.11, IT1.3
**Dependencies:** T5
**Status:** Completed (structured edit helpers + unit tests added; HTTP/system coverage includes JSON/YAML file-level operation matrix depth with negative-path rollback/audit contract validation)

### T10: Sed-like Text Edits
**Description:** Implement regex/range-based edits with transactional application.
**Requirements:** FR1.17
**Architecture:** 6.5.1 Sed-like edits
**Tests:** UT1.12, IT1.3
**Dependencies:** T5
**Status:** Completed (sed-like edit helpers + unit tests added; HTTP/system coverage includes transactional `operations`, strict validation rollback, and no-op contract checks)

### T11: Validation Framework
**Description:** Implement validation per format with strict/warn/ignore policies and pre/post validation hooks.
**Requirements:** FR1.18
**Architecture:** 6.6 Validation
**Tests:** UT1.13, IT1.3
**Dependencies:** T9, T10
**Status:** Completed (validation helpers + unit tests added; server `json_set_file` flow now enforces post-edit JSON validation)

### T12: Audit Logging & Snapshots
**Description:** Implement append-only audit logging and snapshot management.
**Requirements:** FR1.19, FR1.20, CS1.4
**Architecture:** 6.7 Audit logging, 6.8 Snapshots
**Tests:** UT1.14, UT1.15, ST1.3, ST1.4, IT1.3
**Dependencies:** T5, T11
**Status:** Completed (audit logger/snapshot helpers + unit tests added; integrated into server mutating tool path with IT1.3 coverage)

### T13: Conversion Pipeline
**Description:** Implement conversion pipeline and backend discovery (pandoc/libreoffice/pdfminer).
**Requirements:** FR1.21, CS1.5, NF1.2
**Architecture:** 6.9 Conversion
**Tests:** UT1.16, ST1.5, IT1.6
**Dependencies:** T5
**Status:** Completed (conversion pipeline/backends + unit tests added; conversion response metadata normalized with backend/fallback/error-code contract, explicit `pandoc`/`libreoffice` selection coverage, and conditional real-backend execution tests where tools are installed)

### T14: Tool Registry & Schemas
**Description:** Implement tool registry, schemas, and capability flags.
**Requirements:** FR1.1
**Architecture:** 5. Tool Interface, 11. Extensibility
**Tests:** UT1.17, IT1.1
**Dependencies:** T5
**Status:** Completed (tool registry + unit tests added; FastMCP tool wiring implemented from `file_tools` handlers)

### T15: MCP Server Transport & Dispatch
**Description:** Implement stdio transport and optional HTTP transport with dispatch and error handling.
**Requirements:** FR1.2, FR1.23
**Architecture:** 5. Tool Interface, 10. Error Handling Contract
**Tests:** IT1.1, IT1.8, ST1.2
**Dependencies:** T14
**Status:** Completed (stdio dispatch retained; FastMCP HTTP/SSE runtime + health middleware integrated; deprecated constructor transport settings removed; HTTP integration test coverage added)

### T16: Server Lifecycle Control
**Description:** Implement/standardize start/stop/status workflow for local testing with env file support.
**Requirements:** FR1.22, NF1.6
**Architecture:** 13. POSIX Operational Recommendations
**Tests:** ST1.1, AT1.4
**Dependencies:** T15
**Status:** Completed (pidfile lifecycle improved; CLI start now spawns background serve process with status/stop integration; AT1.4 workflow coverage added)

### T17: Tool Reuse & POSIX Compliance
**Description:** Ensure `file_tools` is server-agnostic and portability requirements are met.
**Requirements:** FR1.24, FR1.25, BO1.3, NF1.5
**Architecture:** Separation rule, 7. Non-Functional Requirements
**Tests:** UT1.18, UT1.19
**Dependencies:** T5, T15
**Status:** Completed (POSIX helpers + unit tests added)

### T18: Observability & Limits
**Description:** Implement log separation and enforce size/timeout limits.
**Requirements:** NF1.2, NF1.3, CS1.5
**Architecture:** 7. Non-Functional Requirements
**Tests:** ST1.6, ST1.7
**Dependencies:** T12, T13
**Status:** Completed (search and conversion size/timeout enforcement covered in ST1.7 with timeout-path verification; search filtering now applies deny rules before result limiting; error payload contract covered)

### T19: Test Suite Implementation
**Description:** Implement all UT/ST/IT/AT tests in `tests/` directory and keep mapping updated.
**Requirements:** NF1.8, BO1.5
**Architecture:** 12. Testing Strategy
**Tests:** All
**Dependencies:** T1-T18
**Status:** Completed (unit/integration/system/application coverage expanded through compound AT workflows and real-backend checks; full-suite regression executed green)

### T20: Documentation Alignment
**Description:** Keep REQUIREMENTS, TASKS, TESTS, and ARCHITECTURE aligned and cross-referenced.
**Requirements:** SV1.1, BO1.5
**Architecture:** 14. Out of Scope (explicit) for exclusions
**Tests:** N/A (doc-only)
**Dependencies:** T19
**Status:** Completed (TESTS/TASKS/CONTEXT-SUMMARY refreshed; API docs/readme/openapi added; full regression evidence recorded)

### T21: API Surface Documentation
**Description:** Add and maintain `openapi.json` and human-readable API usage documentation for health and MCP endpoints.
**Requirements:** FR1.1, FR1.2, FR1.23
**Architecture:** 5. Tool Interface
**Tests:** IT1.1, IT1.8
**Dependencies:** T14, T15
**Status:** Completed (added `openapi.json` and `API_DOCUMENTATION.md`)

### T22: Search Depth/Timeout Controls
**Description:** Add optional search traversal depth and timeout controls and verify behavior through integration flows.
**Requirements:** FR1.9, NF1.2, CS1.5
**Architecture:** 6.2 Search, 7.2 Performance
**Tests:** IT1.4, IT1.9
**Dependencies:** T6, T18
**Status:** Completed (added `max_depth`/`timeout_s` for `search_paths` and `search_content` with integration coverage)

### T23: Integration Story Harness Expansion
**Description:** Add end-to-end story tests that exercise multi-tool CRUD flows, UTF-8 edge cases, conversion optionality, config variants, and audit validation.
**Requirements:** BR1.3, BR1.4, FR1.5, FR1.8, FR1.9, FR1.13, FR1.19, FR1.21
**Architecture:** 12. Testing Strategy
**Tests:** IT1.9, IT1.10, IT1.11
**Dependencies:** T19
**Status:** Completed (added multi-type story, iterative cycle guard, and config matrix harness integration tests)

---

## Requirements → Tasks Mapping (Summary)

- **SV1.x / BO1.x** → T1, T16, T19, T20
- **BR1.x** → T3–T16, T19
- **FR1.1–FR1.25** → T2–T18, T21–T23
- **UC1.x** → T5–T16, T19
- **CS1.x** → T2–T4, T12–T13, T18
- **NF1.x** → T5, T6, T16–T19

---

## Backlog (Unassigned)
None. All requirements mapped to tasks.
