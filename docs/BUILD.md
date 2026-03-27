# file-mcp-server Build Guide

## 1. Prerequisites

- Python 3.10+
- `pip` and virtualenv support
- Access to Cloud-Dog package index (`https://your-package-index/simple/`)
- Docker 24+ (optional for container build/test)

## 2. Local venv setup

```bash
cd ./file-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://your-package-index/simple/
```

## 3. Source build

```bash
python -m build
```

## 4. Docker build

Use the project build wrapper (do not use ad-hoc `docker build`):

```bash
./docker-build.sh registry.example.com/cloud-dog/file-mcp-server:latest
```

## 5. Build and stage web UI bundle (`ui/dist`)

`file-mcp-server` serves the monorepo SPA from `ui/dist/`.

```bash
cd ./cloud-dog-ai-ui-monorepo
npm run build --workspace=apps/file-mcp

cd ./file-mcp-server
mkdir -p ui
rm -rf ui/dist
cp -r ./cloud-dog-ai-ui-monorepo/apps/file-mcp/dist ui/dist
```

Runtime config endpoint:
- `GET /runtime-config.js`
- served dynamically by the backend (no frontend rebuild required per environment)

Optional runtime-config env overrides:
- `FILE_MCP_UI_ENV`
- `FILE_MCP_UI_API_BASE_URL`
- `FILE_MCP_UI_AUTH_MODE`
- `FILE_MCP_UI_AUDIT_LOG_PATH`
- `FILE_MCP_UI_DEFAULT_BROWSE_PATH`
- `FILE_MCP_UI_PROFILE_STORE_PATH`
- `FILE_MCP_UI_BASE_PATH` (default `/ui`)
- `FILE_MCP_UI_DIST_PATH` (default `<repo>/ui/dist`)

## 6. Lint and type-check

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
```

## 7. Test execution by tier

All test runs must include `--env`.

```bash
# QT
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q

# UT
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q

# ST
.venv/bin/python -m pytest tests/system --env tests/env-ST -q

# IT
set -a; source .env.local
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q

# AT
set -a; source .env.local
.venv/bin/python -m pytest tests/application --env tests/env-AT -q
```

## 8. Local runtime start/stop

```bash
./server_control.sh --env tests/env-UT start
./server_control.sh --env tests/env-UT status
./server_control.sh --env tests/env-UT stop
```

## Publication Build Reference

### Dockerfile Location

- Dockerfile: `Dockerfile`
- Build script: `docker-build.sh`
- Primary compose/runtime file: `docker-compose.local.yml`

### Registry Push

```bash
cd ./file-mcp-server
set -a; source .env.local
bash docker-build.sh latest
docker push registry.example.com/cloud-dog/file-mcp-server:latest
```

### Standard Build Arguments and Prerequisites

- `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` when required by the host environment
- Cloud-Dog CA bundle if private trust material is needed
- Vault-backed credentials for private package indexes and registry access
- BuildKit-enabled Docker where the project build script expects it
