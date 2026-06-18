---
template-id: T-RUL
template-version: 1.0
applies-to: RULES.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 24cd1ac046fd3b0da63e4dcfc9cbdc0188ca6947
doc-git-branch: main
doc-source-shas: []
doc-age-policy: indefinite
doc-conformance-stamp: 2026-06-18T09:40:00Z
---

# file-mcp-server — RULES.md

## Common Rules

This project follows the [Cloud-Dog AI Platform Common Rules](../cloud-dog-ai-platform-standards/RULES.md) v2.7+.
Common rules are NOT restated here; consult central for: integrity (§1), environment+config (§2),
server+process management (§3), code+change management (§4), testing (§5), documentation (§6),
repo structure (§7), operational controls (§8), security boundaries (§9), infrastructure
protection (§10), Vault path verification (§11), implementation truthfulness (§12),
sandbox dispatch preconditions (§13, W28A-882 Phase F), completion standards (§14), mandatory reading (§15).

## Project-Specific Rules

### Service Scope

- File tooling only — no LLM integration, no internet crawling, no web search.
- Operate only inside configured scope roots.
- Never edit audit logs or snapshots directly.

### Project Boundaries

- Do not re-run completed migration phases (CONFIG, LOGGING, API-KIT, IDAM) unless explicitly instructed.
- Do not modify repositories outside `file-mcp-server` from this project workflow.

### Verified Port Assignments

Verified against [defaults.yaml](./defaults.yaml):

- API server: `8060`
- Web server: `8061`
- MCP server: `8062`
- A2A server: `8063`

Container split-role mode binds the 8060-8063 set; legacy unified mode uses `port-proxy.py` on
8080-8083. The two modes are mutually exclusive — do not mix them when running with
`--network host`. The container healthcheck probes `127.0.0.1:8000` which is a false-negative in
split-role mode; rely on per-port `/health` instead. See [AGENT-LESSONS.md](./AGENT-LESSONS.md)
W28A-845 §7 and §1 for the canonical write-up.

### Split-Role vs Unified Docker Mode

- Split-role mode: four processes on ports 8060/8061/8062/8063, one role each (api/web/mcp/a2a).
- Unified mode: single FastAPI process behind `port-proxy.py`.
- For Docker audit validation and integration testing, prefer the single-server port from the env
  file; the proxy conflicts with `--network host` on the split-role ports.

### Audit JSONL Path Resolution

- The audit JSONL sink path resolves from `profile.audit.log_path` via `${FILE_MCP_AUDIT_LOG}` in
  `defaults.yaml`. Shell `export` is overridden by env file values loaded via
  `_seed_process_env_from_file()` with `os.setdefault()` — the earliest env file to set
  `FILE_MCP_AUDIT_LOG` wins.
- IDAM audit events (user/group/api-key CRUD) go to the platform application logger as
  `admin_identity_audit` messages, NOT into the JSONL audit sink. MCP tool events go through
  `_write_audit()` → `AuditLogger.write()` → JSONL. These are two separate paths; an empty JSONL
  with populated `admin_identity_audit` entries in the app log is expected, not a regression.

### Profile-Based Jobs Config

- `profiles.default.jobs.*` requires nested Pydantic models — flat dict overrides at the profile
  level do not validate. See AGENT-LESSONS.md §9 (W28A-661) for the model layout.

### DB-Backed Admin Identity / SQLite Contention

- `FileStorageProfile` (dynamic profiles) and `FilePlatformDbState` (service-level platform state)
  use `cloud_dog_db`. SQLite-backed deployments can show write contention between admin operations
  and auth resolution in split-role mode; use the platform-recommended backend (Postgres) for
  any high-concurrency deployment.

### Test Env Files (committed, non-secret)

- `tests/env-UT` — unit test config
- `tests/env-ST` — system test config
- `tests/env-IT` — integration test config

Vault sections used by this project: `dev.storage` (S3/WebDAV/FTP backend credentials),
`dev.keys` (API keys), `dev.repository` (PyPI/NPM registry credentials).

## Incident Records

Authoritative incident write-ups for this service live in
[AGENT-LESSONS.md](./AGENT-LESSONS.md). The following local incidents must not be deleted from
this repository and remain binding on agents working on file-mcp-server:

- **W28A-845 — Native Playwright, web proxy, UI contracts.** Includes the Docker healthcheck
  false-negative in split-role mode (§7) and the `port-proxy.py` 8080-8083 conflict with
  `--network host` (§ end of W28A-845 block).
- **W28A-636 — Audit JSONL path resolution precedence; IDAM-vs-MCP audit separation.**
  Earliest-env-file-wins behaviour for `FILE_MCP_AUDIT_LOG`; two separate audit paths.
- **W28A-661 — Profile-based jobs config needs nested Pydantic models.**
- **W28A-823 — S3 copy header fix.** `If-None-Match` destination precondition; file-mcp
  Dockerfile pin (installs packages directly, not via pyproject); cloud-dog-storage 0.1.5.
- **W28A-824 — Search backend-native.** `cloud_dog_storage.search()` S3 ListObjectsV2 / WebDAV
  SEARCH + PROPFIND-infinity; file-mcp `search_path_names` delegates with `iter_paths` fallback;
  cloud-dog-storage 0.1.6. Old `iter_paths` 13.6s/27.2s → new 0.17s/0.89s.
- **W28A-961 — file-mcp sweep, stack recovery, and evidence capture.** Mixed local runtime state
  can present as four unrelated UI regressions; recover the stack before re-investigating. QT
  bespoke greps must be scoped to `main.py` and `mcp_tool_audit_shim.py` for the W28A-961 gates;
  wider-repo matches are out of scope for that specific gate.

If an incident write-up is added, removed, or amended in `AGENT-LESSONS.md`, this list MUST be
updated in the same change. Removing an incident record requires explicit coordinator sign-off.
