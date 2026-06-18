---
template-id: T-BLR
template-version: 1.0
applies-to: BUILD.md
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
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T09:40:00Z
---

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

If platform packages are available from a package index instead of editable
source checkouts, install from a single index (no `--extra-index-url`):
```bash
PYPI_URL=https://pypi.org/simple
pip install -e ".[dev]" --index-url "$PYPI_URL"
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

### UI Bundle
The exported tree includes the UI files used by the Docker build. Rebuild the UI only if you maintain a separate UI source tree.

### Docker Container
```bash
# Public boundary (default): single public index, no internal host.
PUBLICATION_TAG_SUFFIX=github-test ./docker-build.sh latest --variant public
```

Explicit package source and CA example:
```bash
PYPI_URL=https://pypi.org/simple \
CUSTOM_CA_CERT=./certs/ca.pem \
PUBLICATION_TAG_SUFFIX=github-test ./docker-build.sh latest --variant public
```

For an internal/preprod developer build that resolves platform packages from the
internal mirror, use `--variant dev` (this requires internal network access and
is not part of the public publication path):
```bash
./docker-build.sh latest --variant dev
```

## Docker Push
```bash
docker push registry.example.com/team/file-mcp-server:latest
```

## Configuration
Port and runtime configuration come from shell environment variables, the env file passed to `server_control.sh`, and `defaults.yaml`.

## Local Secrets
Put local-only values in the env file passed to `server_control.sh` or mounted into Docker. Do not commit real credentials.
