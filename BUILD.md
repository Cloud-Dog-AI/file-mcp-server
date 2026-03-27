# Build Instructions

## Project
`file-mcp-server` - file operations service with API, Web, MCP, and A2A surfaces.

## Prerequisites
- Python 3.10+
- Node.js 20+ and npm 10+ for the UI bundle
- Docker with BuildKit support

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

If local platform packages are available from a package index instead of editable source checkouts:
```bash
PYPI_URL=https://packages.example.com/simple/
pip install -e ".[dev]" --extra-index-url "$PYPI_URL"
```

## Local Configuration
```bash
cat > .env.local <<'ENV'
CLOUD_DOG__API_SERVER__PORT=8060
CLOUD_DOG__WEB_SERVER__PORT=8061
CLOUD_DOG__MCP_SERVER__PORT=8062
CLOUD_DOG__A2A_SERVER__PORT=8063
FILE_MCP_HTTP_PORT=8062
FILE_MCP_STORAGE_ROOT=./data/storage
ENV
```

## Run Locally
```bash
./server_control.sh --env ./.env.local start all
./server_control.sh --env ./.env.local status all
./server_control.sh --env ./.env.local stop all
```

## Run Tests
```bash
.venv/bin/python -m pytest tests/quality --env ./.env.test -v
.venv/bin/python -m pytest tests/unit --env ./.env.test -v
.venv/bin/python -m pytest tests/system --env ./.env.test -v
.venv/bin/python -m pytest tests/integration --env ./.env.test -v
.venv/bin/python -m pytest tests/application --env ./.env.test -v
```

## Build
### Python Package
```bash
python -m pip install build
python -m build
```

### Build and Stage the UI Bundle
```bash
cd ../cloud-dog-ai-ui-monorepo
npm install
npm run build --workspace=apps/file-mcp
cd ../file-mcp-server
mkdir -p ./ui
rm -rf ./ui/dist
cp -r ../cloud-dog-ai-ui-monorepo/apps/file-mcp/dist ./ui/dist
```

### Docker Container
The Docker build script can auto-discover editable platform packages from `.venv`, or you can provide them explicitly:
```bash
./docker-build.sh registry.example.com/team/file-mcp-server:latest
```

Explicit source and CA example:
```bash
CLOUD_DOG_SITE_PACKAGES=.venv/lib/python3.10/site-packages \
CLOUD_DOG_CONFIG_SRC=../cloud-dog-ai-platform-standards/packages/backend/platform-config \
CLOUD_DOG_LOGGING_SRC=../cloud-dog-ai-platform-standards/packages/backend/platform-logging \
CLOUD_DOG_DB_SRC=../cloud-dog-ai-platform-standards/packages/backend/platform-db \
CLOUD_DOG_JOBS_SRC=../cloud-dog-ai-platform-standards/packages/backend/platform-jobs \
CUSTOM_CA_CERT=./certs/ca.pem \
./docker-build.sh registry.example.com/team/file-mcp-server:latest
```

## Docker Push
```bash
docker push registry.example.com/team/file-mcp-server:latest
```

## Configuration
Port and runtime configuration come from shell environment variables, the env file passed to `server_control.sh`, and `defaults.yaml`.

## Vault Integration
```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your-token
export VAULT_MOUNT_POINT=your-mount
export VAULT_CONFIG_PATH=your-path
```
