# file-mcp-server Deployment Guide

## 1. Docker deployment

Build:
```bash
./docker-build.sh registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

Run (single container):
```bash
docker run --rm --name file-mcp-server \
  --network=host \
  -v "$(pwd)/tests/env-IT:/app/.env:ro" \
  -e FILE_MCP_ENV_PATH=/app/.env \
  registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

Compose (local):
```bash
docker compose -f docker-compose.local.yml --env-file tests/env-IT-local-docker up -d
```

## 2. Bare metal deployment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
./server_control.sh --env tests/env-IT start
```

Use systemd/supervisor wrapper to call `server_control.sh --env <env-file> serve`.

## 3. Terraform integration

Deployment manifests are managed externally under `cloud-dog-repo/terraform/`.
This repository consumes those artefacts; it does not mutate Terraform state.

## 4. Vault integration

Load Vault environment before IT/AT runtime operations:

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
bash scripts/validate-vault.sh
```

Primary Vault paths consumed by this service:
- `dev.storage.s3.*`
- `dev.storage.webdav.*`
- `dev.storage.ftp.*`
- `dev.storage.google_drive.*`
- `dev.databases.filemcp_dev_mysql.*`
- `dev.databases.filemcp_dev_postgresql.*`

## 5. Database options

- SQLite (development/default)
  - `CLOUD_DOG__DB__DIALECT=sqlite`
  - `CLOUD_DOG__DB__DATABASE=./database/file_mcp.db`
- PostgreSQL (preprod/prod)
  - `CLOUD_DOG_DB__DIALECT=postgresql`
  - `CLOUD_DOG_DB__HOST`, `PORT`, `USERNAME`, `PASSWORD`, `DATABASE`
- MySQL (optional)
  - `CLOUD_DOG_DB__DIALECT=mysql`
  - `CLOUD_DOG_DB__HOST`, `PORT`, `USERNAME`, `PASSWORD`, `DATABASE`

Migrations are executed through `cloud_dog_db` runtime bootstrap.

## 6. VDB options

Not applicable for `file-mcp-server`.
No vector database dependency is required for this service.

## 7. LLM configuration

Not applicable for `file-mcp-server`.
The service does not implement model/runtime LLM integration.

## 8. Health checks

- `GET /health`
- `GET /ready`
- `GET /live`

Expected healthy response includes `ok/status` runtime indicators without secret material.

## 9. Monitoring and logs

- Server log path: `FILE_MCP_SERVER_LOG`
- Audit log path: `FILE_MCP_AUDIT_LOG`
- Correlation-aware structured logs are emitted through `cloud_dog_logging`.
- Endpoint health state is queryable via MCP tool `backend_status`.
