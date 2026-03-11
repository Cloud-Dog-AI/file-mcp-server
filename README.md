# file-mcp-server

Deterministic, scoped file operations exposed over MCP transports (`streamable-http`, `http`, `sse`).

License: Apache-2.0  
Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.
Release status: Release Candidate

## What this server provides

- Secure scoped file tools (`read_file`, `write_file`, `move_path`, `delete_file`, `list_dir`, etc.)
- Search and diff tools (`search_content`, `search_paths`, `diff_text`, `diff_files`)
- Structured document tooling (JSON, YAML, XML, HTML, Markdown)
- Validation, conversion, base64 utilities, and transactional sed-like edits
- Audit + snapshot support for mutating operations
- Configurable FastMCP HTTP runtime with API key auth

## Quick start (local Python)

```bash
bash scripts/setup_venv.sh
source .venv/bin/activate
mkdir -p private
cp docker-env.example private/env-test
PYTHONPATH=src ./server_control.sh --env private/env-test serve
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

## Docker quick start

Build:

```bash
./docker-build.sh cloud-dog/file-mcp-server:latest
```

Run on host network:

```bash
mkdir -p run/workspace run/logs
cp docker-env.example run/env.base
```

```bash
docker run --rm --name file-mcp-server \
  --network=host \
  -v "$(pwd)/run/workspace:/workspace" \
  -v "$(pwd)/run/logs:/workspace/logs" \
  -v "$(pwd)/run/env.base:/workspace/env.base:ro" \
  -e FILE_MCP_ENV_PATH=/workspace/env.base \
  cloud-dog/file-mcp-server:latest
```

Detailed Docker deployment, certs, multi-config, and remote host examples:
- `DOCKER-README.me`
- `docker-env.example`
- `env-docker-example` (preprod all-4-in-one multi-profile env template)
- `docker-config.profiles.example.yaml` (single-container multi-profile template: local/s3/webdav/ftp)

## Configuration model

Precedence order (highest first):
1. Environment variables (`docker run -e ...`)
2. `--env-path` file(s) (comma-separated; left to right)
3. `config.yaml`
4. `defaults.yaml`

Primary Docker runtime variables:
- `FILE_MCP_ENV_PATH`
- `FILE_MCP_PROFILE`
- `FILE_MCP_CONFIG_PATH`
- `FILE_MCP_DEFAULTS_PATH`
- `FILE_MCP_TLS_CA_BUNDLE`
- `FILE_MCP_STORAGE_BACKEND` (`local|webdav|ftp|s3|google_drive`)
- `FILE_MCP_STORAGE_TLS_INSECURE` / `FILE_MCP_STORAGE_TLS_CA_BUNDLE` (remote backends)
- `FILE_MCP_ENDPOINT_HEALTH_*` (startup probe + retry/recovery policy)

For multi-profile deployments, mount a custom `config.yaml` with multiple profiles and select using:
- `FILE_MCP_PROFILE=<profile-name>`
- Per-request override is also supported:
  - query parameter `profile=<name>`
  - header `X-File-MCP-Profile: <name>`

## CERTS support

Mount your certificate bundle into the container and point to it:

```bash
docker run --rm --network=host \
  -v "$(pwd)/certs:/app/certs:ro" \
  -e FILE_MCP_TLS_CA_BUNDLE=/app/certs/ca.crt \
  ...
```

Entry-point logic installs this CA into container trust and exports TLS env vars for Python/curl.

WebDAV move resilience is configurable through env/config:
- `FILE_MCP_WEBDAV_MOVE_RETRY_COUNT`
- `FILE_MCP_WEBDAV_MOVE_RETRY_BACKOFF_S`
- `FILE_MCP_WEBDAV_MOVE_PROBE_TIMEOUT_S`
- `FILE_MCP_WEBDAV_MOVE_RETRY_STATUSES`

## Managing server lifecycle

### Native lifecycle helper

```bash
./server_control.sh --env private/env-test start
./server_control.sh --env private/env-test status
./server_control.sh --env private/env-test stop
```

### In container

```bash
docker exec -it file-mcp-server ./server_control.sh --env /workspace/env.base status
```

## MCP tools (summary)

- File tools: `read_file`, `write_file`, `copy_file`, `move_file`, `move_path`, `rename_path`, `delete_file`, `create_dir`, `chmod_path`, `list_dir`
- Search tools: `search_paths`, `search_content`
- Validation tools: `validate_text`, `validate_file`
- Diff and base64: `diff_text`, `diff_files`, `b64_encode`, `b64_decode`, `b64_encode_file`, `b64_decode_to_file`
- Structured tools: JSON/YAML/XML/HTML/Markdown get/set/merge/move/copy and `*_file` variants
- Advanced tools: `convert_file`, `sed_edit_file`, `meld_files` (optional)
- Runtime status: `backend_status` (endpoint state per profile/backend)

## HTTP/API surface

- `GET /` (status summary page; JSON when `Accept: application/json`)
- `GET /health`
- `POST /mcp`
- `GET /admin/google-drive` (admin UI enabled only)
- `POST /admin/google-drive/start` (admin UI enabled only)
- `GET /admin/google-drive/callback` (admin UI enabled only)
- `POST /admin/reload` (admin UI enabled only)

OpenAPI specification:
- `openapi.json`
- `API_DOCUMENTATION.md`

## Testing

Full suite:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest
```

Docker-focused tests:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest tests/integration/IT1.2_DockerContainerRuntime/test_docker_container_runtime.py -k command -q
```

```bash
source .venv/bin/activate
FILE_MCP_RUN_DOCKER_TESTS=1 PYTHONPATH=src \
pytest tests/integration/IT1.2_DockerContainerRuntime/test_docker_container_runtime.py -q
```

Expanded remote matrix + Docker suite:

```bash
source .venv/bin/activate
FILE_MCP_RUN_DOCKER_TESTS=1 \
FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS=1 \
FILE_MCP_RUN_REMOTE_MATRIX_TESTS=1 \
PYTHONPATH=src pytest -q
```

Optional remote Docker host:

```bash
FILE_MCP_RUN_DOCKER_TESTS=1 FILE_MCP_DOCKER_HOST=tcp://remote-docker-host:2375 \
PYTHONPATH=src pytest tests/integration/IT1.2_DockerContainerRuntime/test_docker_container_runtime.py -q
```

## Additional docs

- `DOCKER-README.me`
- `API_DOCUMENTATION.md`
- `migration/verify/README.md`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TASKS.md`
- `docs/TESTS.md`

## Google Drive interactive setup

Use the interactive helper to configure Google Drive credentials into your preferred env file:

```bash
./scripts/setup-google-drive.sh private/env-google-drive
```

Equivalent direct command:

```bash
python scripts/google_drive_setup.py --env-path private/env-google-drive
```

It prompts for:
- Google account email
- Folder id, folder share URL, or folder name
- OAuth client id/secret
- Authorization code
- Target env file path

Then it validates token + folder access and writes `FILE_MCP_GDRIVE_*` settings.

When using a localhost redirect URI (for example `http://localhost`), the setup script can auto-capture the authorization code from the callback and continue without manual copy/paste.

## Server-hosted Google Drive setup pages

For client-site deployments where the server is remote, use built-in admin pages:

1. Enable admin UI in env:
   - `FILE_MCP_ADMIN_UI_ENABLED=true`
   - optionally set `FILE_MCP_ADMIN_UI_TOKEN=<secret>`
2. Open:
   - `http(s)://<server-host>:<port>/admin/google-drive`
   - if token is set, pass `?token=<secret>` or header `X-Admin-Token: <secret>`
3. Select target profile and complete OAuth flow.
   - Profile-pinned mode: open `/admin/google-drive?profile=<name>` to lock profile selection.
   - Form values are remembered on refresh (except client secret).

Use an OAuth **Web application** credential in Google with redirect URI:
- `http(s)://<server-host>:<port>/admin/google-drive/callback`

### Apply config without restart

- `POST /admin/reload` hot-reloads the active profile registry from current env/config/defaults.
- The same admin gate applies (`FILE_MCP_ADMIN_UI_ENABLED` and optional token).
- If `FILE_MCP_ADMIN_APPLY_ON_CALLBACK=true`, successful `/admin/google-drive/callback` auto-runs reload.

### How to get `FILE_MCP_GDRIVE_CLIENT_ID` and `FILE_MCP_GDRIVE_CLIENT_SECRET`

1. Open Google Cloud Console: `https://console.cloud.google.com/`
2. Create/select a project.
3. Enable **Google Drive API**:
   - APIs & Services -> Library -> Google Drive API -> Enable
4. Configure OAuth consent screen:
   - APIs & Services -> OAuth consent screen
   - choose External (or Internal), set app details
   - in **Audience**, keep Publishing status as `Testing` during development
   - add test users (must include the account used to log in)
5. Create credentials:
   - APIs & Services -> Credentials -> Create Credentials -> OAuth client ID
   - Application type: **Web application**
   - add Authorized redirect URI(s), for example:
     - `http://127.0.0.1:8000/admin/google-drive/callback`
     - `http://<host-or-dns>:8000/admin/google-drive/callback`
6. Copy values from the created credential:
   - Client ID -> `FILE_MCP_GDRIVE_CLIENT_ID`
   - Client secret -> `FILE_MCP_GDRIVE_CLIENT_SECRET`

### Google OAuth troubleshooting (common)

- **Google hasn’t verified this app**:
  - expected for test-mode apps
  - ensure your login account is listed in OAuth consent screen -> **Audience** -> **Test users**
  - continue via `Advanced` -> `Go to <app> (unsafe)` (test users only)
- **Where is Publishing status?**
  - Google Cloud Console -> APIs & Services -> OAuth consent screen -> **Audience** section
  - label appears as `Publishing status` (`Testing` or `In production`)
- **Unauthorized / redirect mismatch**:
  - ensure OAuth client type is **Web application**
  - ensure the Redirect URI entered in file-mcp-server exactly matches one Authorized redirect URI in Google
  - host, scheme (`http/https`), port, and path must match exactly
