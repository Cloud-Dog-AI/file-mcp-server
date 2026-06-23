---
template-id: T-RUC
template-version: 1.1
applies-to: docs/ROLES-AND-USECASES.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-23
doc-git-commit: 157f34c69faf321586cdb0ec962c0f4a9d1a3f1b
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-23T14:02:08Z
---

# file-mcp-server — ROLES-AND-USECASES

> **Template version:** T-RUC v1.1 — uplifted in W28E-1802A with a canonical UC-NNN inventory
> (§8) that Stream-B and Stream-C bind their tests and pages against.

## 1. Roles

Canonical roles from `PS-83-canonical-role-catalog.md` plus the service-local operator persona.

| Role | From | Notes |
|---|---|---|
| `admin` | platform | Full access: storage-profile CRUD, user/group/API-key management, RBAC, Google-Drive OAuth binding, config reload. |
| `read-write` | platform | Data write: file CRUD, structured/sed edits, conversion, search, dry-run preview within authorised profiles. |
| `read-only` | platform | Data read: browse, read, search, download, and inspect audit within authorised profiles; all mutating actions denied (403). |
| `anon` | platform | Unauthenticated. Static WebUI assets are public; all data/MCP/A2A/admin surfaces are denied (401). |
| `service` | platform | Machine api-key principal (agent/automation) calling MCP/A2A/API tools under a profile's key. |
| `operator` | local | Local engineer running lifecycle (start/stop/status), endpoint-health, and observability flows; maps to `admin` for RBAC. |

## 2. Personas

| Persona | Description | Roles |
|---|---|---|
| Platform admin | Provisions storage profiles, users, groups, API keys, and Google-Drive bindings. | `admin` |
| Automation/agent | Calls file tools over MCP/A2A under a scoped api-key. | `service`, `read-write` |
| Integration engineer | Runs safe-edit / conversion / search workflows against local and remote backends. | `read-write` |
| Compliance reviewer | Reads audit trails, snapshots, and operational logs. | `read-only` |
| Anonymous visitor | Reaches the login page; everything else is gated. | `anon` |

## 3. Use cases

**You MUST include:** UC-001…UC-NNN. One row per persona+goal pair. The canonical machine-readable
inventory is §8; this section is the narrative cross-surface view.

| UC ID | Persona | Goal | Surface (REST/MCP/A2A/WEBUI) | Requirements | Tests |
|---|---|---|---|---|---|
| `UC-001` | Automation/agent | Discover and call file tools with health/error contracts | MCP, REST, A2A | `FR-001`, `FR-007`, `FR-009`, `FR-017` | `UT1.24_ToolsRegistry`, `IT1.23_ServerHttpIntegration` |
| `UC-003` | Integration engineer | Safe structured/sed edit with validation, snapshot, audit | MCP, REST | `FR-004`, `FR-005`, `FR-006` | `UT1.7_EditStructured`, `ST1.6_SystemDryRunContract` |
| `UC-019` | Read-only / read-write | Browse a storage-profile-scoped file tree in the WebUI | WEBUI | `FR-012`, `FR-016` | `AT_WEBUI_EndToEnd`, `AT1.13_ApplicationWebUiAdmin` |

## 4. Negative use cases (admin/security)

Tests for refused/forbidden flows — required to prove RBAC.

| UC ID | Persona | Attempted | Expected | Test |
|---|---|---|---|---|
| `UC-022` | Anonymous visitor | Read data / call MCP / call A2A without a key | `401` | `UT1.35_FlatRoleLogin` (`CS-005`–`CS-008`) |
| `UC-021` | Read-only | Write/delete a file or edit a profile | `403` | `UT1.35_FlatRoleLogin` (`CS-009`–`CS-012`) |
| `UC-023` | Any authenticated | Call a tool with a missing/invalid required parameter | `422` | `ST1.8_SystemErrorContract` (`CS-013`–`CS-016`) |

## 5. Cross-references

- [REQUIREMENTS.md](REQUIREMENTS.md)
- [TESTS.md](TESTS.md)
- PS-82-access-control-session-test-matrix.md
- PS-83-canonical-role-catalog.md
- PS-COMMON-SVC-REQ (CSR-005/006/016/035 — common authn/RBAC/WebUI taxonomy, pinned by reference)

## 6. Project-specific notes

- The recovered `UC-CFG-01` (new file storage profile for a project folder) is preserved as the
  worked profile-lifecycle example below and is now covered by `UC-015`/`UC-016` + `CFG-01`–`CFG-04`.
- file-mcp's surface set is **api, mcp, a2a, webui**. The WebUI-specific narrative requirements
  (`FR1.37`–`FR1.47`) are exercised by the WebUI use cases (`UC-019`–`UC-024`) and are the explicit
  drive-out targets for Stream-C; W28A-651 / `WEBUI-REVIEW.md` observations map to those use cases
  (see TESTS.md §3 WebUI acceptance drive-out rows).

## 8. Canonical Use-Case Inventory (UC-NNN) — W28E-1802A

This is the canonical, machine-readable use-case inventory (PS-REQ-TEST-TRACE §2/§3.5). Each UC
names its primary actor(s), goal, surfaces, and the FR/CS/CFG rows it drives. These UC-NNN rows are
the stable identifiers Stream-B and Stream-C bind their tests and pages against.

Actors: `admin`, `read-write`, `read-only`, `anon`, `service`, `operator`.

| UC | Actor(s) | Goal | Surfaces | Requirements |
|---|---|---|---|---|
| `UC-001` | any authenticated / service | Discover and call file tools across MCP/A2A/HTTP API with health, error contracts, and correlation IDs | api, mcp, a2a, webui | `FR-001`, `FR-007`, `FR-009`, `FR-017`, `FR-024` |
| `UC-002` | admin / operator | Run the service with layered configuration, Vault-backed secrets, reusable `file_tools`, and no hard-coded values | internal, api | `FR-013`, `FR-010`, `NF-001`, `NF-002` |
| `UC-003` | read-write | Perform a safe structured/sed edit workflow (read → diff → edit → validate → snapshot → audit) | mcp, api | `FR-004`, `FR-005`, `FR-006`, `FR-019` |
| `UC-004` | read-write | Convert a PDF/Office document to Markdown/text with warnings where best-effort | mcp, api | `FR-008` |
| `UC-005` | read-write | Preview a dry-run edit diff without modifying files | mcp, api | `FR-003` |
| `UC-006` | read-only / operator | Inspect the audit trail, operational logs, and snapshot history | api, webui | `FR-022`, `FR-019`, `NF-003` |
| `UC-007` | operator | Start/stop/status the server for local testing via the approved env-file workflow | internal | `FR-028` |
| `UC-008` | read-write | Run the safe-edit workflow against a configured remote backend within scope and limits | mcp, api | `FR-012`, `FR-027` |
| `UC-009` | read-only | Search filenames and content across a remote backend root with depth/timeout/result limits | mcp, api | `FR-012`, `FR-019`, `FR-029` |
| `UC-010` | operator | Start the server, receive endpoint health status, and observe consistent retry/recovery/failure reporting | internal, api | `FR-009`, `FR-014`, `FR-020` |
| `UC-011` | read-write / admin | Perform scoped file operations against a configured Google Drive folder using OAuth-managed credentials | api, mcp | `FR-015`, `FR-021` |
| `UC-012` | operator | Enable the restart-threshold policy and have the server exit deterministically when endpoint failures reach the threshold | internal | `FR-020` |
| `UC-013` | admin | Bind Google Drive to a profile through admin pages and have the server apply the updated profile without restart | api, webui | `FR-015` |
| `UC-014` | operator / any | Run one server instance with multiple profiles and select the profile per request via query/header | api, mcp, webui | `FR-016` |
| `UC-015` | admin | Create a new file storage profile (scope roots, backend, auth, limits, validation, snapshots, audit) at runtime | api, mcp, webui | `FR-016`, `CFG-01` |
| `UC-016` | admin | Read, update, and delete an existing storage profile through its full lifecycle | api, mcp, webui | `CFG-02`, `CFG-03`, `CFG-04`, `FR-016` |
| `UC-017` | admin | Manage users, groups, and API keys with RBAC across API/MCP/WebUI | api, mcp, webui | `CFG-08`, `CFG-09`, `CFG-10`, `CFG-11`, `CS-009` |
| `UC-018` | system | Emit an audit event for every CRUD/mutation with user identity, action, timestamp, and outcome | internal | `CFG-12`, `NF-003` |
| `UC-019` | read-only / read-write | Browse a storage-profile-scoped file tree in the WebUI File Browser with type icons and metadata | webui | `FR-012`, `FR-016` |
| `UC-020` | read-only | Search in the WebUI scoped to the selected storage profile and open a result in browser context | webui | `FR-019`, `FR-016` |
| `UC-021` | read-only | Attempt a mutating action and be denied (403); a read-write user succeeds | webui, api, mcp | `CS-009`, `CS-010`, `CS-011`, `CS-012` |
| `UC-022` | anon | Be denied data/MCP/A2A surfaces (401) while static WebUI assets remain public | api, mcp, a2a, webui | `CS-005`, `CS-006`, `CS-007`, `CS-008`, `FR-024` |
| `UC-023` | any authenticated | Submit a missing/invalid required parameter and receive a structured 422 rejection | api, mcp, a2a, webui | `CS-013`, `CS-014`, `CS-015`, `CS-016`, `FR-006` |
| `UC-024` | admin / operator | Inspect the WebUI dashboard, settings, jobs, and about surfaces using governed shared components | webui | `FR-016`, `FR-027` |

### Recovered domain content — `archive/2026-06-12/USE_CASES.md` (worked example)

#### UC-CFG-01 New File Storage Profile For A Project Folder (now covered by `UC-015`/`UC-016`)

1. Provision a new file profile scoped to a dedicated project subfolder.
2. Confirm the profile exposes only its configured scope roots.
3. Create a dated subfolder and upload markdown and PDF content.
4. Read, edit, rename, search, and delete those files using the profile.
5. Update the profile to adjust limits or storage behaviour.
6. Re-run file operations and verify the new policy is enforced.
7. Delete the profile and confirm it can no longer be selected for later operations.
