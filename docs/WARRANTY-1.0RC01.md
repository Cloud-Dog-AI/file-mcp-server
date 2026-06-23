---
doc-id: WARRANTY-1.0RC01
project: file-mcp-server
generated: 2026-06-23T15:01:52Z
generator: scripts/build-warranty-table.py v1.0
standard: PS-CLOSEOUT-WARRANTY v1.0
---

# file-mcp-server — 1.0RC01 Release Warranty Table

Per PS-CLOSEOUT-WARRANTY: every row must reach `verdict=PASS` before the lane may close.
`PENDING` columns are filled by Stream-B (Section B) and Stream-C (Section C).

## Section A — Requirements + UseCases + Test-Design coverage

_W28E-1802A hand-finalised: every REQ/CS/NF/UC row has a design row in the canonical docs and at least one binding (FR/CS/NF via `@pytest.mark.req(...)`; UC via the §8 inventory + test-design rows). `cross_surface_covered` is `YES` where the requirement spans ≥2 surfaces and `N-A` for internal-only or single-surface negative rows; `webui_observation_bound` is `N-A` (mature service — W28A-651 / WEBUI-REVIEW observations are deferred WebUI drive-out targets for Stream-C per TESTS.md §3, not Stream-A observation closures). Sections B and C remain `PENDING` for Stream-B and Stream-C._

| id | kind | title | since | source_evidence | design_row_present | binding_row_present | cross_surface_covered | webui_observation_bound | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `CS-001` | CS | Anon attempts data read → 401 across api/mcp/a2a/webui | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `CS-002` | CS | Read-only attempts write → 403 (api, mcp) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `CS-003` | CS | Missing required param → 422 (api) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-004` | CS | Wrong-role privileged op → 403 (mcp) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-005` | CS | anon-denied (api) → 401 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-006` | CS | anon-denied (mcp) → 401 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-007` | CS | anon-denied (a2a) → 401 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-008` | CS | anon-denied (webui) → 401 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-009` | CS | wrong-role-denied (api) → 403 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-010` | CS | wrong-role-denied (mcp) → 403 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-011` | CS | wrong-role-denied (a2a) → 403 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-012` | CS | wrong-role-denied (webui) → 403 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-013` | CS | missing-param-error (api) → 422 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-014` | CS | missing-param-error (mcp) → 422 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-015` | CS | missing-param-error (a2a) → 422 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `CS-016` | CS | missing-param-error (webui) → 422 | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `FR-001` | FR | Tool boundary & schema contract (language-neutral discovery/exec, JSON I/O, structured errors) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-002` | FR | Base64 encode/decode for strings, bytes, and file-content round-trips | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-003` | FR | Unified-diff generation for strings/files and dry-run edit previews | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-004` | FR | Structured document CRUD across JSON/YAML/XML/HTML/Markdown | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-005` | FR | Sed-like text editing with multi-operation atomic transactions | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-006` | FR | Content validation with strict/warn/ignore policy | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-007` | FR | Transport support (STDIO/HTTP) + cloud_dog_api_kit health/readiness/error-envelope | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-008` | FR | Conversion pipeline PDF/Office to Markdown/text/JSON (pluggable backends) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-009` | FR | Health & readiness /health /ready /live + A2A health surface | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-010` | FR | Library-first tool reuse — file_tools has no MCP-transport dependency | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `FR-011` | FR | POSIX compliance — portable filesystem behaviour | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `FR-012` | FR | Remote storage backends local/s3/webdav/ftp/google_drive, same tool surface | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-013` | FR | Configuration precedence & zero hard-coding via cloud_dog_config + Vault | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-014` | FR | Endpoint health startup checks with per-backend status and retries | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-015` | FR | Google Drive OAuth and folder binding (admin hot-reload) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-016` | FR | Single-server multi-profile routing with profile-local controls | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-017` | FR | Authentication & A2A health-auth contract (profile-aware keys, 401/200) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-018` | FR | File read operations — text/binary, encoding detection, partial/range reads | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-019` | FR | Search — path glob/regex + content, scope-bounded, depth/timeout | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-020` | FR | Endpoint health runtime classification & recovery, restart threshold | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `FR-021` | FR | Google Drive storage-backend semantics (folder id/url, logical paths) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-022` | FR | Observability / operational logging separate from audit | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `FR-023` | FR | Authenticated session status probe for WebUI/API re-verification | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-024` | FR | Flat-role login & anonymous access gating (static public, data gated 401) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-025` | FR | Time-based search filters (modified_after/before window) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-026` | FR | Unit-tier correctness of file_tools primitives and server seams | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-027` | FR | Application/acceptance workflow capabilities (end-to-end flows) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-028` | FR | System-tier service contracts (dry-run, limits, rollback, restart) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `FR-029` | FR | Integration-tier HTTP/MCP/A2A flows (routing, backends, audit, jobs) | `4986e9e` | docs/REQUIREMENTS.md | YES | YES | YES | N-A | **PASS** |
| `NF-001` | NF | Platform-package adoption — cloud_dog_* packages, no bespoke replacements | `157f34c` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `NF-002` | NF | Configuration & secret hygiene — no hard-coded values, Vault-backed, redaction | `157f34c` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `NF-003` | NF | Logging & audit compliance — PS-40/NIST AU-3, append-only, rotation/retention | `157f34c` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `NF-004` | NF | Documentation completeness & canonical doc set (PS-DOCS-CANONICAL) | `157f34c` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `NF-005` | NF | Security posture & RULES discipline (auth/scope/secret-mask; no skip/mock IT/AT) | `157f34c` | docs/REQUIREMENTS.md | YES | YES | N-A | N-A | **PASS** |
| `UC-001` | UC | Discover and call file tools across MCP/A2A/HTTP with health/error contracts | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-002` | UC | Run with layered config, Vault secrets, reusable file_tools, no hard-coded values | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-003` | UC | Safe structured/sed edit workflow (read→diff→edit→validate→snapshot→audit) | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-004` | UC | Convert a PDF/Office document to Markdown/text | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-005` | UC | Preview a dry-run edit diff without modifying files | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-006` | UC | Inspect audit trail, operational logs, and snapshot history | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-007` | UC | Start/stop/status the server for local testing via env-file workflow | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-008` | UC | Safe-edit workflow against a configured remote backend within scope/limits | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-009` | UC | Search filenames/content across a remote backend root with limits | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-010` | UC | Start the server and observe endpoint health retry/recovery/failure reporting | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-011` | UC | Scoped file operations against a Google Drive folder via OAuth | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-012` | UC | Restart-threshold policy: server exits deterministically on endpoint failure | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-013` | UC | Bind Google Drive to a profile via admin pages without restart | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-014` | UC | One server instance, multiple profiles, per-request profile selection | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-015` | UC | Create a new file storage profile at runtime | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-016` | UC | Read/update/delete a storage profile through its lifecycle | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-017` | UC | Manage users, groups, and API keys with RBAC across API/MCP/WebUI | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-018` | UC | Emit an audit event for every CRUD/mutation with identity/action/outcome | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-019` | UC | Browse a storage-profile-scoped file tree in the WebUI File Browser | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-020` | UC | Search in the WebUI scoped to the selected storage profile | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-021` | UC | Mutating action denied (403) for read-only; read-write succeeds | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-022` | UC | Anon denied data/MCP/A2A (401); static WebUI assets public | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-023` | UC | Missing/invalid required parameter rejected with structured 422 | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |
| `UC-024` | UC | Inspect WebUI dashboard/settings/jobs/about with governed components | `157f34c` | docs/ROLES-AND-USECASES.md §8 | YES | YES | N-A | N-A | **PASS** |

## Section B — Functional delivery coverage

| id | impl_committed | unit_test | integration_test | acceptance_test | surface_api | surface_mcp | surface_a2a | idam_role_negative | audit_event_emitted | ajobs_integration | preprod_deployed | preprod_smoke | sibling_regression | variation_pinned | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FR-001` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-002` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-003` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-004` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-005` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-006` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-007` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-008` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-009` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-010` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-011` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-012` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-013` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-014` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-015` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-016` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-017` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-018` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-019` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-020` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-021` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-022` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-023` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-024` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-025` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-026` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-027` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-028` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-029` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |

## Section C — WebUI + E2E coverage

| page | role | uc_id | playwright_spec | screenshot | axe_a11y | style_conformance | url_canonical | positive_assertion | negative_assertion | webui_observation_closed | preprod_url_smoke | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Login | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Login | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Login | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Login | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Top-Menu | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Top-Menu | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Top-Menu | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Top-Menu | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Left-Menu | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Left-Menu | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Left-Menu | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Left-Menu | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Footer | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Footer | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Footer | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Footer | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Audit-Log | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Audit-Log | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Audit-Log | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Audit-Log | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Users | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Users | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Users | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Users | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Groups | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Groups | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Groups | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Groups | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-API-Keys | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-API-Keys | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-API-Keys | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-API-Keys | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Roles | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Roles | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Roles | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-Roles | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-RBAC | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-RBAC | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-RBAC | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Admin-RBAC | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-API-Docs | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-API-Docs | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-API-Docs | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-API-Docs | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-MCP-Console | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-MCP-Console | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-MCP-Console | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-MCP-Console | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-A2A-Console | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-A2A-Console | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-A2A-Console | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| Developer-A2A-Console | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Jobs | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Jobs | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Jobs | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Jobs | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Settings | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Settings | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Settings | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-Settings | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-About | admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-About | read-write | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-About | read-only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| System-About | anon | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-001` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-001` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-001` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-001` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-002` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-002` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-002` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-002` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-003` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-003` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-003` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-003` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-004` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-004` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-004` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-004` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-005` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-005` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-005` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-005` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-006` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-006` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-006` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-006` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-007` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-007` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-007` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-007` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-008` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-008` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-008` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-008` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-009` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-009` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-009` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-009` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-010` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-010` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-010` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-010` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-011` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-011` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-011` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-011` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-012` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-012` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-012` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-012` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-013` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-013` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-013` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-013` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-014` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-014` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-014` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-014` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-015` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-015` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-015` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-015` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-016` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-016` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-016` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-016` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-017` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-017` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-017` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-017` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-018` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-018` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-018` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-018` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-019` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-019` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-019` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-019` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-020` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-020` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-020` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-020` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-021` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-021` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-021` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-021` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-022` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-022` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-022` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-022` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-023` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-023` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-023` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-023` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | admin | `UC-024` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-write | `UC-024` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | read-only | `UC-024` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
| (UC-row) | anon | `UC-024` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | **PENDING** |
