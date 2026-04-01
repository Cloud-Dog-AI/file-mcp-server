# File MCP Server - Context Summary (Agent Handover)

## Snapshot
- Repository: `/opt/iac/Development/cloud-dog-ai/file-mcp-server`
- Branch: `main`
- HEAD commit: `7462e7bbedaf6269fcd1ba5ba511294fac25ec4e`
- Date context: March 31, 2026

## Last Completed Instruction
- Completed: `W28A-501-FILEMCP-E2E-TEST-1`
- Report: `working/W28A-501-FILEMCP-E2E-TEST-1-REPORT.md`
- Previous: `W28A-516-FIX-FILEMCP-TEST-SUITE` (`working/W28A-516-FIX-TEST-SUITE-REPORT.md`)

## W28A-501 E2E Test #1 Result
- Round 1 (Local Docker): **27/27 PASS**
- Round 2 (Preprod): **27/27 PASS**
- All 4 storage backends tested: local, S3, WebDAV, FTP
- Full RBAC lifecycle tested: user/group/key CRUD, selective profile access, grant/revoke, admin denial, user disable
- Evidence: 27 JSON files + 2 screenshots per round, 159+ audit log entries, `working/W28A-501-round1-results.json`, `working/W28A-501-round2-results.json`

### Code Fixes Applied in W28A-501
Three bugs were discovered and fixed during E2E testing:

1. **Multi-profile MCP routing** (`src/file_mcp_server/idam_adapter.py`):
   - Added `refresh_profiles()` method to `MultiProfileApiKeyTokenVerifier`
   - Auth verifier's profile list was not refreshed when profiles were dynamically created via admin API
   - Now called from `_reload_registry()` after config reload

2. **Profile context propagation** (`src/file_mcp_server/server_runtime.py`, `src/file_mcp_server/idam_adapter.py`):
   - `RequestContextMiddleware` now extracts profile from `x-file-mcp-profile` header or `?profile=` query param and sets context variable
   - `verify_access_token()` reads context variable instead of always defaulting
   - FastMCP's single-token auth flow now respects per-request profile selection

3. **Dynamic key resolver error logging** (`src/file_mcp_server/idam_adapter.py`):
   - Exceptions from dynamic API key resolver were silently swallowed
   - Added warning-level logging with error type and message

### Product Gaps Documented Honestly
- Time-based search (`modified_after`) not supported by `search_paths` tool
- No read-only permission level — `profile:{name}` scope grants full access
- S3 `create_dir` not supported (virtual directories auto-created on write)

## Deploy Status (W28A-501)
- Docker image pushed:
  - `registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest`
  - Evidence: `working/w28a-501-docker-push.log`
  - Digest: `sha256:7f877152843e140ab9117a9be0cdb81ef4a9b76600234cf732d78eefb34b6e11`
- Terraform scoped apply completed:
  - Targets: `docker_image.filemcpserver`, `docker_container.filemcpserver0`
  - Result: 2 added, 0 changed, 2 destroyed
- Health check post-deploy: all 4 backends healthy (ftp, local, s3, webdav)

## Verified Test Outcome (W28A-516)
- Command used: `python3 -m pytest tests/ -v --env tests/env-AT --tb=short`
- Evidence: `working/w28a-516-final-results-r3.txt`
- Final result: `321 passed, 2 skipped, 0 failed, 0 errors`
- Skips are Google Drive live tests (expected in this cycle).

## Important Code/Test Changes in This Cycle
- **W28A-501 bug fixes** (see above): `idam_adapter.py`, `server_runtime.py`
- WebUI E2E hardening and auth/login stability:
  - `tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py`
- Admin UI compatibility assertions (SPA + legacy admin HTML):
  - `tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py`
- Docker IT prerequisite helper image bootstrap:
  - `tests/integration/_docker_source_images.py`
- UT1.22 fallback route accept-header alignment:
  - `tests/unit/UT1.22_ServerRuntime/test_server_runtime.py`

## Current Worktree State (Critical for Next Agent)
- Worktree is dirty with many tracked modifications and untracked generated artifacts.
- **This is the authorised baseline** — do not assume clean. Proceed on top of this state.
- Key modified tracked files in `src/`:
  - `src/file_mcp_server/idam_adapter.py` (W28A-501 fixes)
  - `src/file_mcp_server/server_runtime.py` (W28A-501 fixes)
  - `src/file_mcp_server/main.py`
  - `src/file_tools/storage/*.py`, `src/file_tools/search/find.py`
- Untracked generated files under `src/` (`read-target-*`, `edit-target-*`, `w28a429-search-marker-*`, `.lock` files)
- Untracked helper/test files:
  - `tests/integration/_docker_source_images.py`
  - `tests/test_st_time_based_search.py`
- Deleted tracked db file: `database/chat-client.db`

## Available Related Artifacts
- Prior instruction reports/log bundles exist under `working/`:
  - `W28A-408-*`, `W28A-429-*`, `W28A-447-*`, `W28A-457-*`
  - `W28A-480-*`, `W28A-487-*`, `W28A-488-*`, `W28A-510-*`, `W28A-516-*`
  - `W28A-501-*` (current instruction — report, evidence JSONs, screenshots, test scripts)

## Operational Notes for Next Agent
- Always source vault before test/deploy commands when required:
  - `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`
- Docker build requires explicit package source paths:
  - `CLOUD_DOG_CONFIG_SRC`, `CLOUD_DOG_LOGGING_SRC`, `CLOUD_DOG_DB_SRC`, `CLOUD_DOG_JOBS_SRC`
  - All at `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-{name}`
- Preprod admin API key: `FileMCP-local-5678` (no admin UI token set)
- Preprod container name: `filemcpserver0.app.vpc0.cloud-dog.net`
- Preprod local storage root: `/workspace`
- This environment has hit unified exec session limits during long runs — reuse sessions, avoid parallel long-lived shells.

## Recommended Next Step on Agent Change
- Start from latest requested instruction after W28A-501.
- Re-read both rules files before modifications:
  - `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/RULES.md`
  - `/opt/iac/Development/cloud-dog-ai/file-mcp-server/RULES.md`
- Validate current dirty state with `git status --short` before making edits.
- Note: W28A-501 code fixes have NOT been committed — they are in the dirty worktree.
