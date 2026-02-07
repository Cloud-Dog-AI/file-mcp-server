# File MCP Server — TESTS.md
Version: 0.1 • 2026-02-05
Status: Draft

## Purpose
This document defines the test plan for `file-mcp-server`, aligned to:
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TASKS.md`
- `RULES.md` (100% compliance)

Every requirement MUST map to at least one test. Tests MUST use real filesystem operations and configuration-driven inputs.

---

## Test Principles (Rules Compliance)

- **Real systems only** for Integration (IT) and Application (AT) tests.
- **No hardcoded values**: all paths, keys, and settings come from `os.environ → env file → config.yaml → defaults.yaml`.
- **Unit tests use temporary env/config files** created in `tmp_path` and must not rely on committed env fixtures.
- **Env file required** when the server or test harness expects one (e.g., `--env private/env-<name>`).
- **Stop on failure**: do not continue running further tests until failures are resolved.

---

## Test Types

- **UT (Unit Tests)**: Isolated modules; may use temp directories but must exercise real code paths.
- **ST (System Tests)**: End-to-end system component checks (server runtime, audit, snapshots).
- **IT (Integration Tests)**: API/tool-level flows across components using real services.
- **AT (Application Tests)**: User workflows and realistic scenarios across multiple tools.

---

## Test Folder Structure

```
tests/
  unit/
    UT1.1_ConfigLoader/
    UT1.2_Auth/
    ...
  system/
    ST1.1_ServerLifecycle/
    ...
  integration/
    IT1.1_ToolCatalog/
    ...
  application/
    AT1.1_EndToEndWorkflow/
    ...
```

Folder names must match test IDs and map to entries in this document.

---

## Environment & Pre-Conditions

- System/Integration/Application tests use a dedicated test workspace (scoped root) and `private/env-test` env file.
- Unit tests create temporary env/config files in `tmp_path` and must not depend on committed env fixtures.
- The env file must contain all required secrets/keys.
- No tests may rely on absolute hardcoded paths; use config values only.
- Ensure server lifecycle control uses approved scripts (no direct process management).

---

## Environment Files & Log Locations

- **Env files:** `private/env-<name>` (or `.env` when explicitly required by tooling).
- **Operational logs:** `logs/` (server runtime logs).
- **Audit logs:** path configured via config (default example: `.file-mcp/audit.log.jsonl` in scope).
- **Snapshots:** path configured via config (default example: `.file-mcp/snapshots/` in scope).
- **Test run artefacts:** `working/test-runs/<test-id>/` (stdout, stderr, inputs, outputs, diffs).
- **Test data:** `tests/<type>/<test-id>/data/` (when persistent fixtures are required).

---

## Test Run History Template

Maintain the last 5 runs per test using the format below:

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| YYYY-MM-DD | UT1.1   | private/env-test | pytest ... | PASS/FAIL | Summary | working/test-runs/UT1.1/run-YYYYMMDD/ |

Each test section’s **Run History** should be updated using this template.

---

## Coverage Map (Requirements → Tests)

### Scope/Vision (SV)
- **SV1.1** → ST1.1, AT1.1
- **SV1.2** → UT1.1
- **SV1.3** → IT1.2, IT1.3, IT1.4
- **SV1.4** → AT1.3

### Business Goals/Objectives (BO)
- **BO1.1** → IT1.2, AT1.1
- **BO1.2** → IT1.3, ST1.3
- **BO1.3** → UT1.18
- **BO1.4** → ST1.1, AT1.4
- **BO1.5** → ST1.1

### Business/Application Requirements (BR)
- **BR1.1** → IT1.1, IT1.8
- **BR1.2** → IT1.3, ST1.3
- **BR1.3** → IT1.2, IT1.4
- **BR1.4** → UT1.7, UT1.16, IT1.5, IT1.6
- **BR1.5** → UT1.1, UT1.2, UT1.3
- **BR1.6** → ST1.1, AT1.4

### Functional Requirements (FR)
- **FR1.1** → UT1.17, IT1.1
- **FR1.2** → IT1.1, IT1.8
- **FR1.3** → UT1.1
- **FR1.4** → UT1.1
- **FR1.5** → UT1.2, ST1.2
- **FR1.6** → UT1.3, IT1.2
- **FR1.7** → UT1.4, IT1.2
- **FR1.8** → UT1.4, IT1.2
- **FR1.9** → UT1.5, IT1.4
- **FR1.10** → UT1.6, IT1.7
- **FR1.11** → UT1.7, IT1.5
- **FR1.12** → UT1.8, IT1.5
- **FR1.13** → UT1.9, UT1.10, UT1.11, IT1.3
- **FR1.14** → UT1.9
- **FR1.15** → UT1.10
- **FR1.16** → UT1.11
- **FR1.17** → UT1.12
- **FR1.18** → UT1.13, IT1.3
- **FR1.19** → UT1.14, ST1.3, IT1.3
- **FR1.20** → UT1.15, ST1.4, IT1.3
- **FR1.21** → UT1.16, ST1.5, IT1.6
- **FR1.22** → ST1.1, AT1.4
- **FR1.23** → ST1.2, IT1.8
- **FR1.24** → UT1.18, IT1.1
- **FR1.25** → UT1.19

### Use Cases (UC)
- **UC1.1** → IT1.2, AT1.1
- **UC1.2** → IT1.3, AT1.1
- **UC1.3** → IT1.4
- **UC1.4** → IT1.6, AT1.2
- **UC1.5** → IT1.5, AT1.1
- **UC1.6** → ST1.3, AT1.1
- **UC1.7** → ST1.1, AT1.4

### Cyber Security (CS)
- **CS1.1** → UT1.2, ST1.2
- **CS1.2** → UT1.3, IT1.2
- **CS1.3** → UT1.1
- **CS1.4** → UT1.14, ST1.3
- **CS1.5** → ST1.7, IT1.6

### Non-Functional (NF)
- **NF1.1** → UT1.4, IT1.3
- **NF1.2** → UT1.5, ST1.7
- **NF1.3** → ST1.6
- **NF1.4** → UT1.9, UT1.10, UT1.11
- **NF1.5** → UT1.19
- **NF1.6** → ST1.1
- **NF1.7** → UT1.1
- **NF1.8** → ST1.1

---

## Unit Tests (UT)

**Unit test configuration:** Unit tests generate temporary env/config files (see `tests/config_helpers.py`) and clear any environment overrides after execution. No committed env fixtures are permitted.

### UT1.1: Config Loader Precedence & Profiles
**Goal/Outcome:** Confirm configuration precedence and profile selection are deterministic and fail fast when required settings are missing.
**Scope:** Config loader, env expansion, profile selection.
**Summary:** Validate precedence order (os.environ → env file → config.yaml → defaults.yaml) and ensure required keys are enforced without hardcoded values.
**Requirements:** FR1.3, FR1.4, CS1.3, NF1.7
**Architecture:** 3. Configuration and Precedence
**Tasks:** T2
**Preconditions:**
- Temporary env files created in `tmp_path` (multi-env precedence exercised).
- Temporary `defaults.yaml` + `config.yaml` fixtures reference env vars via `${...}`.
**Postconditions:**
- Environment variables set for the test are cleared/reset.
**Steps:**
1. Load config with env file and verify expansion.
2. Set `os.environ` overrides and reload; confirm precedence.
3. Remove required env vars and verify loader fails fast.
**Expected:** Precedence order respected; missing required configuration fails predictably.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.1 | N/A (tmp env files) | pytest tests/test_config_loader.py | FAIL | ModuleNotFoundError: file_tools (PYTHONPATH not set) | N/A |
| 2026-02-05 | UT1.1 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_config_loader.py | PASS | 2 passed | N/A |

### UT1.2: API Key Authentication & Redaction
**Goal/Outcome:** Ensure authentication rejects invalid keys and redacts secrets from logs.
**Scope:** Auth config and redaction logic.
**Summary:** Exercise valid/invalid key paths using config-sourced keys only.
**Requirements:** FR1.5, CS1.1
**Architecture:** 4.1 Authentication
**Tasks:** T3
**Preconditions:**
- Auth keys provided via env/config chain using temporary env/config files.
- Logging configured to capture auth messages.
**Postconditions:**
- Auth log output stored for inspection and cleaned up.
**Steps:**
1. Authenticate with valid key from config.
2. Attempt invalid key and expect rejection.
3. Inspect logs to confirm redaction.
**Expected:** Unauthorized calls rejected; secrets never logged.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.2 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_auth.py | PASS | 5 passed | N/A |

### UT1.3: Scope Policy Traversal & Allow/Deny
**Goal/Outcome:** Prevent out-of-scope access and traversal attempts.
**Scope:** Scope policy evaluation and path normalization.
**Summary:** Validate allow/deny globs and traversal rejection within configured roots.
**Requirements:** FR1.6, CS1.2
**Architecture:** 4.2 Authorisation via Scope Policy
**Tasks:** T4
**Preconditions:**
- Scope roots and globs sourced from config/env chain (temporary env/config files).
- Scoped test files created under the configured root.
**Postconditions:**
- Temporary test files removed from scoped root.
**Steps:**
1. Attempt access within scope; expect allow.
2. Attempt traversal (`../`) and deny glob matches; expect rejection.
3. Verify logs/audit capture denial.
**Expected:** Out-of-scope access denied; events logged.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.3 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_scope_policy.py | FAIL | 4 failed, 1 passed: reason `not_in_allowlist` mismatched expected deny reasons | N/A |
| 2026-02-05 | UT1.3 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_scope_policy.py | FAIL | 4 failed, 1 passed: `**/` patterns still not matching root-level files (reason `not_in_allowlist`) | N/A |
| 2026-02-05 | UT1.3 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_scope_policy.py | PASS | 5 passed | N/A |

### UT1.4: Filesystem Operations (Atomic Writes)
**Goal/Outcome:** Ensure file operations are atomic and correct.
**Scope:** Read/write/move/copy/delete operations under scope.
**Summary:** Use real filesystem operations and verify atomic rename behavior.
**Requirements:** FR1.7, FR1.8, NF1.1
**Architecture:** 6.1 Core file operations
**Tasks:** T5
**Preconditions:**
- Scoped root configured via env/config chain.
- Test file paths derived from scoped root.
**Postconditions:**
- All temporary files removed.
**Steps:**
1. Write file via tool function and verify contents.
2. Move/rename file and verify atomicity (no partial reads).
3. Copy/delete and verify expected filesystem state.
**Expected:** Atomic writes and correct content across operations.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.4 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_filesystem.py | PASS | 5 passed | N/A |

### UT1.5: Search Utilities
**Goal/Outcome:** Validate search results and limit enforcement.
**Scope:** Filename/content search with max results and size limits.
**Summary:** Search scoped directories using config-driven limit values.
**Requirements:** FR1.9, NF1.2
**Architecture:** 6.2 Search
**Tasks:** T6
**Preconditions:**
- Search limits configured via env/config chain (temporary env/config files).
- Scoped test files created under configured root.
**Postconditions:**
- Test files removed.
**Steps:**
1. Search by path and by content.
2. Verify deny globs exclude matches.
3. Verify max results and max file size limits enforced.
**Expected:** Correct matches returned within configured bounds.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.5 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_search.py | PASS | 6 passed | N/A |

### UT1.6: Base64 Encode/Decode
**Goal/Outcome:** Validate base64 round-trip accuracy.
**Scope:** Base64 encode/decode helpers.
**Summary:** Encode file content and bytes from real files.
**Requirements:** FR1.10
**Architecture:** 6.3 Base64
**Tasks:** T7
**Preconditions:**
- Sample files created under scoped root.
**Postconditions:**
- Sample files cleaned up.
**Steps:**
1. Encode file content.
2. Decode and compare to original bytes.
**Expected:** Exact round-trip match.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.6 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_encoding.py | PASS | 2 passed | N/A |

### UT1.7: Diff Generation
**Goal/Outcome:** Verify unified diff formatting and content.
**Scope:** Diff generation logic.
**Summary:** Compare known inputs and validate diff output format.
**Requirements:** FR1.11
**Architecture:** 6.4 Diff and Meld
**Tasks:** T8
**Preconditions:**
- Sample inputs prepared under scoped root when file-based.
**Postconditions:**
- Sample inputs removed.
**Steps:**
1. Generate diff for strings.
2. Generate diff for files.
3. Validate headers, hunks, and context lines.
**Expected:** Diff output matches expected format and content.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.7 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_diff.py | PASS | 4 passed (includes UT1.8 coverage) | N/A |

### UT1.8: Meld Availability Handling
**Goal/Outcome:** Ensure meld integration fails gracefully when unavailable.
**Scope:** Meld availability detection and warnings.
**Summary:** Validate behavior for enabled/disabled/missing meld.
**Requirements:** FR1.12
**Architecture:** 6.4 Diff and Meld
**Tasks:** T8
**Preconditions:**
- Config toggles provided via env/config chain.
**Postconditions:**
- Any temporary files removed.
**Steps:**
1. Attempt meld invocation with availability disabled.
2. Attempt with missing binary.
3. Confirm warning returned and no crash.
**Expected:** Non-fatal warning behavior; no unhandled errors.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.8 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_diff.py | PASS | 4 passed (includes UT1.7/UT1.8 coverage) | N/A |

### UT1.9: Structured Edits — JSON/YAML
**Goal/Outcome:** Validate CRUD edits for JSON/YAML with deterministic output.
**Scope:** JSON/YAML structured edit engine (create/read/update/delete).
**Summary:** Apply CRUD operations and verify output, diff, and schema validation.
**Requirements:** FR1.13, FR1.14
**Architecture:** 6.5 Structured edits
**Tasks:** T9
**Preconditions:**
- Input files prepared in scoped root.
- Validation mode configured via env/config chain.
**Postconditions:**
- Edited files and diffs captured then cleaned up.
**Steps:**
1. Create nodes/keys; verify output.
2. Update and delete nodes; verify output and diff.
3. Validate deterministic ordering and formatting.
**Expected:** CRUD edits correct; diffs match; deterministic output.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.9 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_edit_structured.py | PASS | 3 passed (UT1.9–UT1.11 coverage) | N/A |

### UT1.10: Structured Edits — XML/HTML
**Goal/Outcome:** Validate XML/HTML structured edits and warnings.
**Scope:** XML/HTML selectors and edit operations.
**Summary:** Apply edits using XPath/CSS and verify warnings on malformed HTML.
**Requirements:** FR1.13, FR1.15
**Architecture:** 6.5 Structured edits
**Tasks:** T9
**Preconditions:**
- Input XML/HTML files prepared in scoped root.
- Validation mode configured via env/config chain.
**Postconditions:**
- Edited files and diffs captured then cleaned up.
**Steps:**
1. Update attributes/nodes via selectors.
2. Validate output serialization and warnings.
**Expected:** Correct edits; warnings emitted only when appropriate.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.10 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_edit_structured.py | PASS | 3 passed (UT1.9–UT1.11 coverage) | N/A |

### UT1.11: Structured Edits — Markdown
**Goal/Outcome:** Validate Markdown section edits without breaking structure.
**Scope:** Markdown heading-path edits.
**Summary:** Replace/insert/extract sections via heading paths.
**Requirements:** FR1.13, FR1.16
**Architecture:** 6.5 Structured edits
**Tasks:** T9
**Preconditions:**
- Markdown fixtures in scoped root.
**Postconditions:**
- Updated files and diffs captured then cleaned up.
**Steps:**
1. Replace section content by heading path.
2. Insert new section and extract section.
3. Verify heading hierarchy preserved.
**Expected:** Correct structure and content updates.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.11 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_edit_structured.py | PASS | 3 passed (UT1.9–UT1.11 coverage) | N/A |

### UT1.12: Sed-like Text Edits
**Goal/Outcome:** Validate sed-like operations and transactional edits.
**Scope:** Regex/range edits with atomic apply.
**Summary:** Apply multiple edits and verify atomicity.
**Requirements:** FR1.17
**Architecture:** 6.5.1 Sed-like edits
**Tasks:** T10
**Preconditions:**
- Input file prepared in scoped root.
**Postconditions:**
- Updated file and diff captured then cleaned up.
**Steps:**
1. Replace pattern and insert lines.
2. Delete range and apply transaction.
3. Validate output and atomic behavior.
**Expected:** All edits applied atomically with correct output.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.12 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_sedlike.py | PASS | 7 passed | N/A |

### UT1.13: Validation Policies
**Goal/Outcome:** Confirm validation modes behave correctly.
**Scope:** strict/warn/ignore validation policies.
**Summary:** Validate invalid inputs across modes with config-driven settings.
**Requirements:** FR1.18
**Architecture:** 6.6 Validation
**Tasks:** T11
**Preconditions:**
- Validation mode set via config/env chain per test case.
**Postconditions:**
- Validation reports stored for inspection.
**Steps:**
1. Validate invalid JSON/HTML with strict mode.
2. Validate with warn mode.
3. Validate with ignore mode.
**Expected:** strict fails; warn passes with warnings; ignore skips.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.13 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_validate.py | PASS | 8 passed | N/A |

### UT1.14: Audit Log Format
**Goal/Outcome:** Ensure audit entries are structured and secrets are redacted.
**Scope:** Audit logging format and append behavior.
**Summary:** Perform mutations and inspect JSONL entries using config-driven log path.
**Requirements:** FR1.19, CS1.4
**Architecture:** 6.7 Audit logging
**Tasks:** T12
**Preconditions:**
- Audit log path configured via env/config chain (temporary env/config files).
**Postconditions:**
- Audit log captured and stored under test artefacts.
**Steps:**
1. Execute mutation operations.
2. Read audit log and validate schema/fields.
3. Confirm no secrets in entries.
**Expected:** Required fields present; no secrets; append-only.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.14 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_audit.py | PASS | 3 passed (includes UT1.14/UT1.15 coverage) | N/A |

### UT1.15: Snapshot Creation & Retention
**Goal/Outcome:** Validate snapshot creation and retention behavior.
**Scope:** Snapshot policy enforcement.
**Summary:** Trigger snapshots via mutations and verify retention policy.
**Requirements:** FR1.20
**Architecture:** 6.8 Snapshots
**Tasks:** T12
**Preconditions:**
- Snapshots enabled and directory configured via env/config chain.
**Postconditions:**
- Snapshot artefacts collected and cleaned up.
**Steps:**
1. Perform mutations that create snapshots.
2. Exceed retention threshold.
3. Verify pruning behavior.
**Expected:** Snapshots created and pruned per policy.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.15 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_audit.py | PASS | 3 passed (includes UT1.14/UT1.15 coverage) | N/A |

### UT1.16: Conversion Pipeline Selection
**Goal/Outcome:** Ensure conversion selects available backends and reports missing ones.
**Scope:** Backend discovery and selection.
**Summary:** Evaluate conversion behavior with config-driven backend lists.
**Requirements:** FR1.21
**Architecture:** 6.9 Conversion
**Tasks:** T13
**Preconditions:**
- Conversion enabled and backend list configured via env/config chain (temporary env/config files).
**Postconditions:**
- Conversion outputs captured for inspection.
**Steps:**
1. Attempt conversion with available backend.
2. Attempt conversion with unavailable backend.
3. Verify warnings and fallback behavior.
**Expected:** Available backend used; missing backend yields warning without crash.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.16 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_convert.py | PASS | 4 passed | N/A |

### UT1.17: Tool Registry & Schemas
**Goal/Outcome:** Ensure tool registry behaves deterministically with schema validation.
**Scope:** Tool registry and schema definitions.
**Summary:** Register a tool and validate schema metadata.
**Requirements:** FR1.1
**Architecture:** 5. Tool Interface, 11. Extensibility
**Tasks:** T14
**Preconditions:**
- Tool definition prepared with input/output schemas.
**Postconditions:**
- Registry reset to initial state.
**Steps:**
1. Register tool definition.
2. Retrieve tool list and inspect schema metadata.
**Expected:** Registry returns consistent definitions.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.17 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_tools_registry.py | PASS | 4 passed | N/A |

### UT1.18: Tool Reuse Outside Server
**Goal/Outcome:** Confirm tool helpers are usable without server runtime.
**Scope:** `file_tools` module reuse.
**Summary:** Directly invoke tool helpers in isolation.
**Requirements:** FR1.24, BO1.3
**Architecture:** Separation rule
**Tasks:** T17
**Preconditions:**
- Config and scope values sourced via env/config chain where needed.
**Postconditions:**
- Any temporary files removed.
**Steps:**
1. Import tool helpers directly.
2. Execute helper operations and validate results.
**Expected:** Helpers work without server dependencies.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.18 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_tool_reuse.py | PASS | 1 passed | N/A |

### UT1.19: POSIX Portability Checks
**Goal/Outcome:** Ensure POSIX portability for file operations.
**Scope:** Path normalization and atomic rename.
**Summary:** Validate path handling without platform-specific assumptions.
**Requirements:** FR1.25, NF1.5
**Architecture:** 7. Non-Functional Requirements
**Tasks:** T17
**Preconditions:**
- POSIX paths used in scoped root.
**Postconditions:**
- Temporary paths removed.
**Steps:**
1. Normalize POSIX paths.
2. Perform rename operations and validate behavior.
**Expected:** No platform-specific assumptions; atomic behavior preserved.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | UT1.19 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_posix.py | PASS | 5 passed | N/A |

---

## System Tests (ST)

### ST1.1: Server Lifecycle & Repo Baseline
**Goal/Outcome:** Validate repository baseline and lifecycle controls.
**Scope:** Server lifecycle scripts and required docs.
**Summary:** Ensure repo structure matches RULES and lifecycle scripts use env files.
**Requirements:** FR1.22, NF1.6, BO1.4, BO1.5
**Architecture:** 2. Repository Layout, 13. POSIX Operational Recommendations
**Tasks:** T1, T16
**Preconditions:**
- `private/env-test` configured with required values.
- Server lifecycle script available (e.g., `server_control.sh`).
**Postconditions:**
- Server stopped cleanly; logs captured.
**Steps:**
1. Verify required docs exist (RULES/REQUIREMENTS/TASKS/TESTS).
2. Start server using lifecycle script with `--env private/env-test`.
3. Verify status and stop server.
**Expected:** Docs present; lifecycle start/status/stop succeed.
**Run History:** None

### ST1.2: Auth Enforcement & Health
**Goal/Outcome:** Validate health endpoints and auth enforcement.
**Scope:** Server health and authentication.
**Summary:** Confirm health checks and key-based access control.
**Requirements:** FR1.5, FR1.23, CS1.1
**Architecture:** 4.1 Authentication, 10. Error Handling Contract
**Tasks:** T3, T15
**Preconditions:**
- Server running via lifecycle script.
- API key configured via env/config chain.
**Postconditions:**
- Server stopped; logs retained.
**Steps:**
1. Call health endpoint.
2. Invoke tool without key; expect rejection.
3. Invoke tool with valid key; expect success.
**Expected:** Health ok; unauthorized rejected; authorized succeeds.
**Run History:** None

### ST1.3: Audit Log Integrity
**Goal/Outcome:** Ensure audit logs are append-only and structured.
**Scope:** Audit log integrity and permissions.
**Summary:** Execute mutations and verify audit log behavior.
**Requirements:** FR1.19, CS1.4
**Architecture:** 6.7 Audit logging
**Tasks:** T12
**Preconditions:**
- Audit log path configured via env/config chain.
- Server running.
**Postconditions:**
- Audit log captured for review.
**Steps:**
1. Execute multiple mutations.
2. Confirm audit log grows and entries are JSONL.
3. Validate permissions as configured.
**Expected:** Append-only log with structured entries.
**Run History:** None

### ST1.4: Snapshot Retention
**Goal/Outcome:** Ensure snapshot retention policy is enforced.
**Scope:** Snapshot retention and pruning.
**Summary:** Create snapshots beyond retention thresholds and verify pruning.
**Requirements:** FR1.20
**Architecture:** 6.8 Snapshots
**Tasks:** T12
**Preconditions:**
- Snapshots enabled and retention configured via env/config chain.
- Server running.
**Postconditions:**
- Snapshot artefacts recorded.
**Steps:**
1. Perform mutations that create snapshots.
2. Exceed retention threshold.
3. Verify pruning behavior.
**Expected:** Old snapshots pruned per policy.
**Run History:** None

### ST1.5: Conversion External Tool Optionality
**Goal/Outcome:** Validate conversion behavior with optional external tools.
**Scope:** Conversion backend availability.
**Summary:** Ensure missing tools produce warnings but no crashes.
**Requirements:** FR1.21
**Architecture:** 6.9 Conversion
**Tasks:** T13
**Preconditions:**
- Conversion enabled; backend list configured via env/config chain.
- Server running.
**Postconditions:**
- Conversion outputs captured.
**Steps:**
1. Disable/omit external tool in config.
2. Run conversion.
3. Inspect warnings and output.
**Expected:** Conversion succeeds or warns appropriately without crashes.
**Run History:** None

### ST1.6: Observability Separation
**Goal/Outcome:** Ensure operational logs are separated from audit logs.
**Scope:** Observability logging configuration.
**Summary:** Execute operations and confirm distinct log outputs.
**Requirements:** NF1.3
**Architecture:** 7.4 Observability
**Tasks:** T18
**Preconditions:**
- Observability log path configured via env/config chain.
- Audit log path configured via env/config chain.
**Postconditions:**
- Logs captured for inspection.
**Steps:**
1. Perform read/write operations.
2. Confirm operational logs do not contain audit entries.
3. Confirm audit log contains mutation entries.
**Expected:** Separate log streams with correct content.
**Run History:**

| Date (UTC) | Test ID | Env File | Command | Status | Notes | Logs/Artefacts |
|------------|---------|----------|---------|--------|-------|----------------|
| 2026-02-05 | ST1.6 | N/A (tmp env files) | PYTHONPATH=src pytest tests/test_observability.py | PASS | 2 passed | N/A |

### ST1.7: Limits & Timeouts
**Goal/Outcome:** Validate limit enforcement for size and timeout settings.
**Scope:** Search limits and conversion timeouts.
**Summary:** Trigger limit conditions and confirm clear errors.
**Requirements:** CS1.5, NF1.2
**Architecture:** 7.2 Performance
**Tasks:** T18
**Preconditions:**
- Limits configured via env/config chain.
- Server running.
**Postconditions:**
- Error responses logged for review.
**Steps:**
1. Perform search that exceeds max results or file size.
2. Trigger conversion timeout.
**Expected:** Limit violations fail with clear errors.
**Run History:** None

---

## Integration Tests (IT)

### IT1.1: MCP Tool Catalog (STDIO)
**Goal/Outcome:** Validate tool discovery and schema handling over stdio.
**Scope:** MCP stdio tool catalog.
**Summary:** Use stdio transport to list tools and invoke a safe read.
**Requirements:** FR1.1, FR1.2
**Architecture:** 5. Tool Interface
**Tasks:** T14, T15
**Preconditions:**
- Server launched with stdio transport and `private/env-test`.
- Scoped root contains readable file.
**Postconditions:**
- Server stopped; logs captured.
**Steps:**
1. Call `tools/list` and capture catalog.
2. Invoke read tool on in-scope file.
**Expected:** Catalog returned; tool invocation succeeds.
**Run History:** None

### IT1.2: Scoped File Operations
**Goal/Outcome:** Validate scoped CRUD file operations.
**Scope:** End-to-end read/write/move/copy/delete within scope.
**Summary:** Perform CRUD inside scope and verify out-of-scope denial.
**Requirements:** FR1.6, FR1.7, FR1.8
**Architecture:** 6.1 Core file operations
**Tasks:** T4, T5
**Preconditions:**
- Server running with scope roots configured.
- Test files created under scope.
**Postconditions:**
- Test files removed; logs collected.
**Steps:**
1. Create, read, update, copy, move, delete within scope.
2. Attempt operation outside scope.
**Expected:** In-scope operations succeed; out-of-scope denied.
**Run History:** None

### IT1.3: Structured Edit Flow with Audit & Snapshot
**Goal/Outcome:** Validate full structured edit flow with audit/snapshot.
**Scope:** Structured edits + validation + audit + snapshots.
**Summary:** Edit JSON/YAML via tool, validate output, verify audit and snapshots.
**Requirements:** FR1.13, FR1.18, FR1.19, FR1.20
**Architecture:** 9.2 Structured edit flow
**Tasks:** T9, T11, T12
**Preconditions:**
- Validation, audit, snapshots configured via env/config chain.
- Server running; test fixtures prepared.
**Postconditions:**
- Audit and snapshot artefacts captured.
**Steps:**
1. Apply structured edit to JSON/YAML file.
2. Validate output based on configured mode.
3. Verify audit entry and snapshot created.
**Expected:** Correct edits with audit and snapshot records.
**Run History:** None

### IT1.4: Search API
**Goal/Outcome:** Validate search tool API behavior end-to-end.
**Scope:** Search content/filename via tool API.
**Summary:** Use search tool to find known content within scope.
**Requirements:** FR1.9
**Architecture:** 6.2 Search
**Tasks:** T6
**Preconditions:**
- Search limits configured via env/config chain.
- Server running; content fixtures in scope.
**Postconditions:**
- Fixtures cleaned up.
**Steps:**
1. Search by filename and content.
2. Validate matches and context lines.
**Expected:** Correct matches returned within configured limits.
**Run History:** None

### IT1.5: Diff & Meld Integration
**Goal/Outcome:** Validate diff tool output and meld integration.
**Scope:** Diff generation via tool API.
**Summary:** Generate diffs and optionally invoke meld based on config.
**Requirements:** FR1.11, FR1.12
**Architecture:** 6.4 Diff and Meld
**Tasks:** T8
**Preconditions:**
- Meld settings configured via env/config chain.
- Server running; input fixtures prepared.
**Postconditions:**
- Diffs stored with test artefacts.
**Steps:**
1. Generate diff via tool.
2. Attempt meld invocation when enabled.
3. Validate warnings when unavailable.
**Expected:** Diff returned; meld handled gracefully.
**Run History:** None

### IT1.6: Conversion End-to-End
**Goal/Outcome:** Validate conversion pipeline end-to-end.
**Scope:** Document conversion via tool API.
**Summary:** Convert documents and validate output and warnings.
**Requirements:** FR1.21
**Architecture:** 6.9 Conversion
**Tasks:** T13
**Preconditions:**
- Conversion enabled; backends configured via env/config chain.
- Server running; input files available in scope.
**Postconditions:**
- Converted outputs captured.
**Steps:**
1. Convert input document to target format.
2. Validate output content and location in scope.
3. Confirm warnings if backend unavailable.
**Expected:** Correct output; warnings only when appropriate.
**Run History:** None

### IT1.7: Base64 File Ops
**Goal/Outcome:** Validate base64 tool operations via API.
**Scope:** Base64 encode/decode through tool interface.
**Summary:** Encode file content and verify decoded output.
**Requirements:** FR1.10
**Architecture:** 6.3 Base64
**Tasks:** T7
**Preconditions:**
- Server running; fixture file in scope.
**Postconditions:**
- Fixture removed.
**Steps:**
1. Encode file content.
2. Decode and compare with original.
**Expected:** Round-trip accuracy.
**Run History:** None

### IT1.8: HTTP Transport & Health
**Goal/Outcome:** Validate HTTP transport and readiness when enabled.
**Scope:** HTTP tool transport and health endpoint.
**Summary:** Start HTTP server and verify health/tool invocation.
**Requirements:** FR1.2, FR1.23
**Architecture:** 5. Tool Interface
**Tasks:** T15
**Preconditions:**
- HTTP transport enabled via config/env chain.
- Server running locally (no external network access).
**Postconditions:**
- Server stopped; logs captured.
**Steps:**
1. Call /health.
2. Invoke a safe tool via HTTP.
**Expected:** Health ok; tool call succeeds.
**Run History:** None

---

## Application Tests (AT)

### AT1.1: End-to-End Safe Edit Workflow
**Goal/Outcome:** Validate full safe-edit workflow with audit trail.
**Scenario:** Read → dry-run diff → edit → validate → audit.
**Summary:** Execute user workflow using real tools and validate outputs.
**Requirements:** UC1.1, UC1.2, UC1.5
**Architecture:** 9.2 Structured edit flow
**Tasks:** T5, T8, T9, T11, T12
**Preconditions:**
- Server running; scope configured via env/config chain.
- Validation/audit enabled via config.
**Postconditions:**
- Audit entries and diffs captured.
**Steps:**
1. Read file and generate dry-run diff.
2. Apply edit and validate output.
3. Verify audit entry created.
**Expected:** Correct edit with diff preview and audit trail.
**Run History:** None

### AT1.2: Conversion + Edit Workflow
**Goal/Outcome:** Validate conversion-to-edit workflow.
**Scenario:** Convert DOCX/PDF → edit Markdown → validate.
**Summary:** Convert document, then apply structured edits and validate.
**Requirements:** UC1.4, FR1.21
**Architecture:** 6.9 Conversion
**Tasks:** T13, T9, T11
**Preconditions:**
- Conversion enabled and backends configured via env/config chain.
- Server running; input files available in scope.
**Postconditions:**
- Converted outputs and diffs captured.
**Steps:**
1. Convert document to Markdown.
2. Apply structured Markdown edits.
3. Validate output per policy.
**Expected:** Converted output editable and valid.
**Run History:** None

### AT1.3: Security Boundary Enforcement
**Goal/Outcome:** Confirm security boundary enforcement.
**Scenario:** Attempt out-of-scope access and verify denial.
**Summary:** Validate deny behavior and audit entries for violations.
**Requirements:** SV1.4, CS1.2
**Architecture:** 4.2 Authorisation via Scope Policy
**Tasks:** T4
**Preconditions:**
- Scope roots configured via env/config chain.
- Server running; audit enabled.
**Postconditions:**
- Audit entries captured.
**Steps:**
1. Attempt out-of-scope read.
2. Attempt out-of-scope write.
3. Verify denials and audit entry.
**Expected:** Access denied; audit entry recorded.
**Run History:** None

### AT1.4: Operator Lifecycle Workflow
**Goal/Outcome:** Validate operator lifecycle workflow.
**Scenario:** Start server with env file, verify health, stop server.
**Summary:** Ensure lifecycle steps succeed using approved scripts.
**Requirements:** FR1.22, UC1.7
**Architecture:** 13. POSIX Operational Recommendations
**Tasks:** T16
**Preconditions:**
- `private/env-test` configured with required values.
- Lifecycle script available.
**Postconditions:**
- Server stopped; logs captured.
**Steps:**
1. Start server using lifecycle script.
2. Verify health endpoint.
3. Stop server and confirm shutdown.
**Expected:** Lifecycle commands succeed; server stops cleanly.
**Run History:** None
