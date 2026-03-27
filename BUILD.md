# Build Instructions

## Project
`file-mcp-server`

## Prerequisites
- Python `3.10+`
- Node.js `20+` and npm `10+` for the SPA bundle
- Docker `24+`
- Access to `https://pypi.cloud-dog.net/simple/`
- Vault bootstrap file: `/opt/iac/Development/cloud-dog-ai/env-vault`

## Local Development Setup
```bash
cd /opt/iac/Development/cloud-dog-ai/file-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```

## Run Locally
```bash
./server_control.sh --env tests/env-IT start all
./server_control.sh --env tests/env-IT status all
./server_control.sh --env tests/env-IT stop all
```

## Run Tests
```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
.venv/bin/python -m pytest tests/system --env tests/env-ST -q
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q
.venv/bin/python -m pytest tests/application --env tests/env-AT -q
```

Database overlays are available in `tests/env-DB-mysql` and `tests/env-DB-postgresql`.

## Build and Stage the Web UI Bundle
```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run build --workspace=apps/file-mcp

cd /opt/iac/Development/cloud-dog-ai/file-mcp-server
mkdir -p ui
rm -rf ui/dist
cp -r /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo/apps/file-mcp/dist ui/dist
```

## Docker Build
```bash
./docker-build.sh registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

## Docker Push
```bash
docker push registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

## Deploy to Preprod
```bash
cd /opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27\ MLAgents
terraform apply -auto-approve
```

## Environment Files
- `tests/env-QT`, `tests/env-UT`, `tests/env-ST`, `tests/env-IT`, `tests/env-AT`
- local overlays: `tests/env-*-local-server`, `tests/env-*-local-docker`, `tests/env-local-docker-server`
- database overlays: `tests/env-DB-mysql`, `tests/env-DB-postgresql`
- defaults: `defaults.yaml`

## Dependencies
- Platform packages: `cloud_dog_api_kit`, `cloud_dog_config`, `cloud_dog_db`, `cloud_dog_idam`, `cloud_dog_jobs`
- Storage/runtime packages: see `pyproject.toml` for the full list.
