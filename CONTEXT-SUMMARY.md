# Context Summary

Version: 1.14 • 2026-02-11
Status: Active (remote storage + endpoint health + Google Drive + expanded matrix/restart tests + admin hot-reload)

## 1) What changed in this cycle

### Storage/backends
- Added/extended multi-backend storage support:
  - `local`, `webdav`, `ftp`, `s3`, `google_drive`
- Added Google Drive backend implementation:
  - `src/file_tools/storage/google_drive.py`
  - OAuth token refresh support
  - folder binding via `folder_id` or `folder_url`
  - deterministic not-supported behavior for unsupported operations (`chmod_path`)
- Storage backend factory updated:
  - `src/file_tools/storage/factory.py` supports `google_drive|gdrive|drive`

### Endpoint health/recovery
- Added runtime endpoint health manager:
  - `src/file_mcp_server/endpoint_health.py`
- Added profile config section:
  - `profiles.<name>.endpoint_health.*`
- Startup probe + retry/recovery wiring added to runtime:
  - `src/file_mcp_server/server.py`
- Added optional restart-exit policy when endpoint threshold is exceeded:
  - `endpoint_health.restart_on_threshold`
  - `endpoint_health.restart_exit_code`
- Added MCP tool:
  - `backend_status` (returns per-backend health state)

### Config/env model
- Added Google Drive config model fields:
  - `storage.google_drive.*`
- Added endpoint health config fields:
  - `endpoint_health.enabled`, `check_on_startup`, `check_all_configured_backends`,
    `max_retries`, `retry_interval_s`, `retry_window_s`,
    `max_failures_before_restart`, `recover_after_s`,
    `restart_on_threshold`, `restart_exit_code`
- Updated:
  - `defaults.yaml`
  - `config.yaml`
  - `docker-env.example`

### OAuth helper
- Added helper script:
  - `scripts/google_drive_oauth_helper.py`
- Purpose:
  - generate Google auth URL
  - exchange auth code
  - print env-variable output for runtime config

### Documentation updates
- Updated/extended:
  - `README.md`
  - `DOCKER-README.me`
  - `docs/REQUIREMENTS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/TESTS.md`

### Tests added
- `tests/test_endpoint_health.py`
  - startup healthy state
  - exception classification
  - recovery after prior failure
- `tests/test_google_drive_storage.py`
  - folder URL -> folder ID parsing
  - required config validation checks
- `tests/test_server_runtime.py`
  - asserts `backend_status` tool is present and callable
- `tests/test_google_drive_oauth_helper.py`
  - OAuth helper URL generation and optional live code exchange flow
- `tests/test_integration_google_drive_live_http.py`
  - env-gated live Google Drive backend integration
- `tests/test_integration_remote_backend_tool_matrix_http.py`
  - broad tool matrix across webdav/ftp/s3 (+google when creds are present)
- `tests/test_system_endpoint_restart_threshold.py`
  - process exit behavior when restart threshold is reached

## 2) Critical fixes during this cycle

- Fixed config validation break when endpoint-health env vars were unresolved placeholders:
  - endpoint-health model fields changed to string-compatible config values
  - parsing is handled by runtime conversion helpers
- Fixed Google Drive backend issues:
  - multipart metadata serialization now uses `json.dumps`
  - fixed f-string escaping bug in Drive query path lookup

## 3) Verified test status

Executed and passing in this environment:
- `PYTHONPATH=src pytest -q tests/test_endpoint_health.py tests/test_google_drive_storage.py tests/test_server_runtime.py`
  - `11 passed`
- `PYTHONPATH=src pytest -q tests/test_integration_remote_storage_backends_http.py tests/test_docker_container_remote_storage_backends.py tests/test_system_conversion_real_backends.py`
  - `5 passed, 3 skipped`
- `PYTHONPATH=src pytest -q tests/test_server_http_integration.py tests/test_config_loader.py`
  - `8 passed`
- `PYTHONPATH=src pytest -q`
  - `148 passed, 7 skipped`
- `FILE_MCP_RUN_DOCKER_TESTS=1 FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS=1 FILE_MCP_RUN_REMOTE_MATRIX_TESTS=1 PYTHONPATH=src pytest -q`
  - `161 passed, 4 skipped`
- Focused expanded suite:
  - `FILE_MCP_RUN_DOCKER_TESTS=1 FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS=1 FILE_MCP_RUN_REMOTE_MATRIX_TESTS=1 PYTHONPATH=src pytest -q tests/test_system_endpoint_restart_threshold.py tests/test_google_drive_oauth_helper.py tests/test_integration_google_drive_live_http.py tests/test_integration_remote_backend_tool_matrix_http.py tests/test_integration_remote_storage_backends_http.py tests/test_docker_container_runtime.py tests/test_docker_container_remote_storage_backends.py`
  - `18 passed, 4 skipped`

Google-specific live status:
- Live Google Drive/OAuth tests are present and runnable.
- They are currently env-gated and skip when Google credentials/auth code are not provided.
- Required flags/vars: `FILE_MCP_RUN_GOOGLE_LIVE_TESTS=1`, `FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST=1`, `FILE_MCP_GDRIVE_*`, and one-time `FILE_MCP_GDRIVE_AUTH_CODE` for exchange tests.

## 4) Execution environment/network timeline (factual)

Observed during this project work:
- Earlier in-session runs occurred under restricted execution settings where direct socket/network operations from the sandboxed command runner failed.
- Later, runner settings changed to a mode with full filesystem access and network enabled, and integration tests requiring local HTTP and remote endpoint calls succeeded.

What this means operationally:
- The repository code does not itself control sandbox ACL/network policy.
- Whether endpoint/network tests can run depends on the active runner policy at execution time.
- Current runner state (this update): network-capable; remote-backend tests are passing.

## 5) Current implementation status

- Multi-backend support: implemented for `local/webdav/ftp/s3/google_drive`.
- Endpoint health startup/recovery framework: implemented and wired.
- Restart-threshold process-exit policy: implemented and tested.
- Deterministic unsupported-backend errors: implemented via `NotSupportedError` contract.
- Docker/env/cert guidance: implemented in docs and templates.

## 6) Latest delta (2026-02-11, hot-reload/admin flow)

Code updates:
- Added missing `escape` import in `src/file_mcp_server/server.py` (OAuth callback success page path).
- Hardened admin gate in middleware so **all** `/admin/*` routes are protected by:
  - `FILE_MCP_ADMIN_UI_ENABLED=true`
  - optional `FILE_MCP_ADMIN_UI_TOKEN` (query `token=` or `X-Admin-Token` header).
- Kept/confirmed `POST /admin/reload` endpoint and wired hot reload callback in HTTP runtime.
- Extended reload callback to rerun endpoint startup health checks and return endpoint health state in response payload.
- Confirmed callback auto-apply path:
  - successful `/admin/google-drive/callback` invokes hot reload when `FILE_MCP_ADMIN_APPLY_ON_CALLBACK=true`.

Test updates:
- Added middleware coverage in `tests/test_server_runtime.py` for:
  - `/admin/reload` blocked when admin UI disabled.
  - `/admin/reload` token enforcement and JSON success payload.
  - `/admin/google-drive/callback` auto-reload execution on successful OAuth callback.

Latest test execution (this run):
- `PYTHONPATH=src pytest -q tests/test_server_runtime.py tests/test_google_drive_admin.py`
  - `11 passed`
- `PYTHONPATH=src pytest -q -k "not live"`
  - `1 failed, 160 passed, 12 skipped, 2 deselected`
  - failing test: `tests/test_integration_remote_storage_backends_http.py::test_remote_storage_backend_end_to_end[webdav]`
  - observed failure: remote WebDAV endpoint returned HTTP 500 on `move_path` (`MOVE`).

Remediation applied after that failure:
- Implemented transient WebDAV `MOVE` retry/backoff with "already applied" detection in `src/file_tools/storage/webdav.py`.
- Added unit coverage in `tests/test_webdav_storage.py` for:
  - transient 5xx retry then success
  - success when operation was already applied despite transient response
  - non-transient hard failure path
- Revalidated:
  - `PYTHONPATH=src pytest -q tests/test_webdav_storage.py` -> `3 passed`
  - `PYTHONPATH=src pytest -q tests/test_integration_remote_storage_backends_http.py::test_remote_storage_backend_end_to_end[webdav] -rs` -> `1 passed`
  - `PYTHONPATH=src pytest -q tests/test_integration_remote_storage_backends_http.py -rs` -> `3 passed`

Additional completion runs:
- `PYTHONPATH=src pytest -q` -> `166 passed, 14 skipped`
- `FILE_MCP_RUN_DOCKER_TESTS=1 FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS=1 PYTHONPATH=src pytest -q tests/test_docker_container_remote_storage_backends.py -rs` -> `3 passed`
- Docker runtime reload validation:
  - `POST /admin/reload` returned `{"ok": true, ...}`
  - MCP `backend_status` returned healthy `local` backend state from the running container.

## 7) Exhaustive backend tool audit (2026-02-11, latest)

Command executed:
- `source .venv/bin/activate && PYTHONPATH=src:. FILE_MCP_EXHAUSTIVE_BACKENDS=webdav,ftp,s3,google_drive FILE_MCP_EXHAUSTIVE_TOOL_TIMEOUT_S=60 python3 scripts/exhaustive_backend_tool_audit.py`

Result summary:
- `webdav: pass=52 not_supported=2 optional_fail=0 fail=0`
- `ftp: pass=52 not_supported=2 optional_fail=0 fail=0`
- `s3: pass=51 not_supported=3 optional_fail=0 fail=0`
- `google_drive: pass=52 not_supported=2 optional_fail=0 fail=0`

Artefact:
- `working/exhaustive_backend_tool_audit.json`

Notes:
- `not_supported` entries are deterministic backend contract responses (for example `chmod_path` on non-POSIX backends).
- No unexpected tool failures remain in this latest exhaustive run.

## 8) Multi-profile single-server routing (2026-02-11)

Implemented:
- One server process now serves multiple profiles concurrently.
- Per-request profile selection:
  - query parameter: `?profile=<name>`
  - header: `X-File-MCP-Profile: <name>`
  - fallback: server default profile (`FILE_MCP_PROFILE` / `--profile`).
- Authentication is profile-aware:
  - selected-profile API keys are enforced
  - cross-profile key reuse is rejected.
- Tool execution is profile-routed with profile-local controls:
  - scope roots, deny/allow globs
  - allowed extensions, read-only extensions
  - limits and backend settings.

Tests added:
- `tests/test_integration_multi_profile_routing_http.py`
  - verifies 5-profile concurrent operation in one server process
  - validates selector + default fallback
  - validates per-profile auth/scope/type controls.
- `tests/test_auth.py` additions for profile-aware verifier behavior.

Verification:
- `PYTHONPATH=src pytest -q tests/test_auth.py tests/test_server_runtime.py tests/test_integration_multi_profile_routing_http.py -rs` -> `22 passed`
- `PYTHONPATH=src pytest -q` -> `172 passed, 14 skipped`
