# Context Summary

Version: 1.21 • 2026-02-20
Status: Release Candidate (multi-profile routing + remote backends + Google Drive admin onboarding)

## 1) Current release-candidate scope

Implemented and validated:
- Multi-profile single-process runtime with per-request profile selection:
  - query `?profile=<name>`
  - header `X-File-MCP-Profile: <name>`
  - default fallback profile
- Profile-aware authentication (API keys scoped to selected profile).
- Storage backends:
  - `local`, `s3`, `webdav`, `ftp`, `google_drive`
- Deterministic backend capability contract:
  - unsupported operations return `Not supported for backend`.
- Endpoint health lifecycle:
  - startup probing, retry/recovery controls, restart-threshold support.
- Admin runtime controls:
  - `/admin/google-drive` OAuth onboarding
  - `/admin/reload` hot profile/config reload
- Root status page (`GET /`) with per-profile health signal and action links.

## 2) Key implementation corrections in this cycle

### 2.1 Configuration precedence compliance
Implemented runtime behavior aligned to `RULES.md`:
1. `os.environ`
2. env file(s)
3. `config.yaml`
4. `defaults.yaml`

Changes:
- `src/file_tools/config/adapter.py`
  - delegates precedence and compile pipeline to `cloud_dog_config`
  - uses `cloud_dog_config` public API only (no bespoke env overlay logic)
  - binds compiled output into existing `ServerConfig` / `ProfileConfig` domain models
- `docker-entrypoint.sh`
  - removed implicit fallback env file behavior
  - only passes `--env-path` when `FILE_MCP_ENV_PATH` is explicitly set

### 2.2 Google Drive admin UX/runtime hardening
- `src/file_mcp_server/server.py`
  - root status page includes profile health/action matrix
  - Google authorize action links include profile pinning (`?profile=<name>`)
  - callback URL generation honors `X-Forwarded-Proto`
- `src/file_mcp_server/google_drive_admin.py`
  - setup page supports locked profile mode
  - form fields persist on refresh via localStorage (excluding client secret)
  - redirect/token URI defaults are restored if blank

### 2.3 Streamable HTTP compatibility for clients
- Added/kept middleware to normalize `Accept` for JSON-only clients on `POST /mcp`
  so streamable-http negotiation does not fail with `406`.

### 2.4 Config migration to cloud_dog_config (PS-80)
- Replaced bespoke config loader internals with `src/file_tools/config/adapter.py` delegating to `cloud_dog_config`.
- Kept `ServerConfig` and `ProfileConfig` as domain models and bound adapter output into them.
- Removed bespoke adapter env parsing/override logic; adapter is a thin bridge (platform load -> thaw -> model bind).

### 2.5 Logging migration to cloud_dog_logging (PS-40)
- Replaced bespoke logging plumbing with platform logging:
  - `src/file_tools/observability.py` now configures `cloud_dog_logging` from loaded profile config.
  - `src/file_tools/audit/adapter.py` maps domain audit events to PS-40 schema while preserving legacy fields required by tests/consumers.
  - `src/file_mcp_server/server.py` switched request correlation to `cloud_dog_logging.correlation` and removed manual JSON serialisation logging.
- Added runtime redaction presets for sensitive fields (`token`, `secret`, `password`, `api_key`).
- Removed direct `print()` usage in server/file_tools logging paths.

### 2.6 External secrets env dependency removed
- Removed default dependency on `/opt/iac/Development/cloud-dog-ai/env-file-mcp-server-secrets`.
- `tests/remote_env_helpers.py` now defaults remote credential loading to `private/env-remote-storage`.
- Deleted `/opt/iac/Development/cloud-dog-ai/env-file-mcp-server-secrets` to prevent accidental reuse.
- Updated `docs/TESTS.md` to match this runtime behaviour.

### 2.7 API Kit migration to cloud_dog_api_kit (PS-20)
- Added `cloud_dog_api_kit` dependency and runtime integration points in transport layer.
- Decomposed monolithic `src/file_mcp_server/server.py` into:
  - thin compatibility export layer (`src/file_mcp_server/server.py`, <200 lines)
  - runtime implementation module (`src/file_mcp_server/server_runtime.py`)
- Added PS-20 endpoint contract behaviour:
  - `/health` now includes `status`, `checks`, `version`
  - added `/ready` and `/live` endpoints
  - admin 4xx responses use envelope shape `{ok:false, errors:[...], meta:{correlation_id}}`
  - removed query-string admin token acceptance; header-only `x-admin-token` remains
- Added migration verification script:
  - `migration/verify/verify-file-mcp-server-API-KIT.sh`

### 2.8 IDAM migration to cloud_dog_idam (PS-70)
- Added `cloud_dog_idam` dependency and introduced `src/file_mcp_server/idam_adapter.py` as the runtime auth bridge.
- Replaced bespoke runtime auth wiring in `src/file_mcp_server/server_runtime.py`:
  - runtime now imports `MultiProfileApiKeyTokenVerifier` from `idam_adapter`
  - no runtime imports from `file_mcp_server.auth`
- Replaced `src/file_mcp_server/auth.py` module body with compatibility re-exports only (no bespoke auth logic retained).
- Implemented profile-aware IDAM API-key verification with FastMCP middleware bridging:
  - per-profile key routing and header/scheme handling preserved
  - request profile context propagation preserved (`get_request_profile_name`)
  - profile scope mapped into IDAM RBAC permissions (`profile:<name>`)
- Added auth decision audit emission with fingerprint-only token identity (no raw API key logging).
- Added migration verification script:
  - `migration/verify/verify-file-mcp-server-IDAM.sh`

## 3) Live deployment state validated

Validated on preprod endpoint:
- `https://filemcpserver0.cloud-dog.net/`
- `https://filemcpserver0.cloud-dog.net/health`

Observed:
- homepage renders profile table with red/green signals
- profiles `default`, `s3`, `webdav`, `ftp`, `google_drive` present
- Google Drive OAuth succeeded and profile health is green
- Google admin route with profile query locks profile selection:
  - `/admin/google-drive?profile=google_drive`

## 4) Test evidence (latest)

### 4.1 Google-first run
Command:
- `source .venv/bin/activate && FILE_MCP_RUN_GOOGLE_LIVE_TESTS=1 PYTHONPATH=src pytest -q tests/test_google_drive_storage.py tests/test_google_drive_admin.py tests/test_google_drive_oauth_helper.py tests/test_google_drive_setup_script.py tests/test_integration_google_drive_live_http.py -rs`

Result:
- `13 passed, 2 skipped`
- skips were expected env-gated live OAuth/live Drive prerequisites.

### 4.2 Full suite run
Command:
- `source .venv/bin/activate && PYTHONPATH=src pytest tests/ -v --env private/env-accept-smoke`

Result:
- `181 passed, 15 skipped` in ~4m04s
- skips remain expected for explicitly flag-gated live/docker/preprod paths.

### 4.3 Focused validation runs for modified areas
- `tests/test_server_runtime.py`, `tests/test_google_drive_admin.py`, `tests/test_config_loader.py` pass with current changes.

### 4.4 Config migration regression gate set
Command:
- `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_config_loader.py tests/test_integration_config_matrix_harness_http.py tests/test_integration_multi_profile_routing_http.py tests/test_system_limits.py tests/test_system_limits_timeout.py tests/test_application_preprod_profile_chain_http.py -v`

Result:
- `12 passed, 1 skipped`
- validates adapter migration path, multi-profile routing, and limits behaviour.

### 4.5 Logging migration gate set
Commands:
- `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_audit.py tests/test_observability.py -v --env private/env-accept-smoke`
- `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_audit.py tests/test_observability.py tests/test_system_audit_integrity.py tests/test_system_snapshot_retention.py tests/test_integration_structured_audit_snapshot.py tests/test_application_search_edit_audit_workflow.py -v --env private/env-accept-smoke`

Results:
- smoke: `5 passed`
- regression: `9 passed`
- runtime checks: audit JSONL parseable with required fields; request-scoped tool logs include correlation IDs (`tool_entries=2`, `missing_correlation=0`); sensitive values redacted (`redaction_leaks=0`).

### 4.6 API Kit migration gate set
Command:
- `bash migration/verify/verify-file-mcp-server-API-KIT.sh`

Result:
- `17 passed, 0 failed` (`ALL PASS`)
- includes prerequisite checks (`CONFIG`, `LOGGING`), smoke/regression suites, and runtime endpoint gates for `/health`, `/ready`, `/live`, 4xx envelope shape, and query-token removal.

### 4.7 IDAM migration gate set
Command:
- `bash migration/verify/verify-file-mcp-server-IDAM.sh`

Result:
- `15 passed, 0 failed` (`ALL PASS`)
- includes prerequisite checks (`CONFIG`, `LOGGING`, `API-KIT`), lint/format/type gates, smoke/regression suites, no-runtime-import gate for legacy auth module, and IDAM-specific gates:
  - unauthenticated protected request rejection
  - low-privilege out-of-scope profile rejection
  - query-string token path regression check
  - fingerprint-only auth audit evidence (no raw API key values)

## 5) What is still intentionally gated (not silently ignored)

The following require explicit flags/credentials and are skipped otherwise:
- preprod AT chain flow (`FILE_MCP_RUN_PREPROD_AT=1`)
- docker integration suites (`FILE_MCP_RUN_DOCKER_TESTS=1`)
- remote backend matrix suite (`FILE_MCP_RUN_REMOTE_MATRIX_TESTS=1`)
- live Google OAuth exchange helper (`FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST=1`)
- live Google Drive backend integration (`FILE_MCP_RUN_GOOGLE_LIVE_TESTS=1` with full `FILE_MCP_GDRIVE_*` credentials)

## 6) Runner environment note (factual)

During this project there were runs under both:
- restricted execution (network/socket-limited)
- unrestricted execution (network-enabled)

This affects whether live endpoint tests can run from this session runner. The application code does not control runner ACL/policy.

## 7) Release-candidate declaration

This repository state is marked as **Release Candidate** for:
- multi-profile runtime routing
- local/s3/webdav/ftp/google_drive backend support
- endpoint health/recovery/restart-threshold controls
- Google Drive admin onboarding and hot reload
- containerized deployment and docs coverage

Use `docs/TESTS.md` for detailed run matrix and gating controls.

## 8) Postmortem: Instruction/Rules Failures (Explicit)

This section records execution failures in this migration cycle, not technical feature gaps.

### 8.1 Failures
- Failed to align quickly to repeated user direction that `env-file-mcp-server-secrets` should no longer be part of active flow.
- Repeatedly explained/defended legacy behaviour instead of immediately executing requested refactor.
- Left the project-local config feedback report stale after upstream instruction/report changes; this created contradictory status between local and authoritative reports.
- Produced contradictory status messaging around the historical `B-1` config blocker until it was re-validated and corrected.
- Required repeated user escalation to perform straightforward instruction-following work that should have been done on first clear directive.

### 8.2 Why this was a rules/process failure
- Priority handling failed: explicit latest instruction updates were not treated as the highest-priority operational truth soon enough.
- Closure discipline failed: old migration artefacts were not reconciled immediately after authoritative report updates.
- Friction to execution was too high: explanation was used where direct action was required.

### 8.3 Corrections now implemented
- Removed external secrets env dependency and deleted the external file.
- Synced local config feedback report to authoritative version and updated wording to reflect deprecation/removal state.
- Added explicit repo-default behaviour pointing to `private/env-remote-storage`.

### 8.4 Hard controls for future turns
- If user gives a direct “remove/stop using X” instruction and it is technically feasible, execute first, explain second.
- When authoritative instruction/report files change, immediately run a local-vs-authoritative parity check and fix drift before any other edits.
- Treat historical migration notes as non-authoritative once superseded by newer instruction versions and explicit stop directives.
