# Context Summary

Version: 1.15 • 2026-02-12
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
- `src/file_tools/config/loader.py`
  - merged env context from env-file values + `os.environ`
  - deterministic env override application to placeholder-declared config paths
  - env interpolation executed against effective merged environment
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
- `source .venv/bin/activate && PYTHONPATH=src pytest -q -rs`

Result:
- `179 passed, 15 skipped` in ~4m06s
- skipped tests are explicit env/flag gated suites (preprod AT, docker gated, remote matrix gated, optional live Google paths).

### 4.3 Focused validation runs for modified areas
- `tests/test_server_runtime.py`, `tests/test_google_drive_admin.py`, `tests/test_config_loader.py` pass with current changes.

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
