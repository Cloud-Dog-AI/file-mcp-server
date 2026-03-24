# PREPROD Deployment — File MCP Server

This document describes the pre-production operator/deployment overlay for this service. The Terraform container environment is the runtime source of truth, and `private/env-PREPROD` is the operator/test overlay used for local control commands and pytest runs against the deployed preprod service. Defaults and non-preprod settings remain documented in `docs/ENV-REFERENCE.md`, `docs/ARCHITECTURE.md`, and `defaults.yaml`.

## 1. Overview
- Service URL: `https://filemcpserver0.cloud-dog.net`
- Container hostname: `filemcpserver0.app.vpc0.cloud-dog.net`
- Health endpoint verified during W28A-241: `https://filemcpserver0.cloud-dog.net/health`
- Docker image: `registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest`
- Active Terraform container definition: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/60 Cloud-Dog AI Containers/filemcpserver_containers.tf.json`
- Legacy/parallel Terraform definition to cross-check when investigating drift: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents/filemcpserver_containers.tf.json`
- Operator overlay file: `/opt/iac/Development/cloud-dog-ai/file-mcp-server/private/env-PREPROD`

### Port allocation
| Surface | Internal port | External URL |
|---|---:|---|
| HTTP/MCP | 8080 | `https://filemcpserver0.cloud-dog.net` |
| MCP path | same process | `https://filemcpserver0.cloud-dog.net/mcp` |
| Health | same process | `https://filemcpserver0.cloud-dog.net/health` |

## 2. Configuration
Section 2 documents the full preprod environment surface that differs from or materially specialises the defaults. Use it together with `defaults.yaml` and `docs/ENV-REFERENCE.md` when tracing a value through the precedence chain `os.environ -> --env file -> config.yaml -> defaults.yaml`.

### HTTP and runtime settings
| Setting(s) | Default / baseline | Preprod source | Preprod change? | Notes |
|---|---|---|---|---|
| `FILE_MCP_HTTP_*` | sourced from env-backed defaults | Terraform + `private/env-PREPROD` | Yes | Preprod uses streamable HTTP on `0.0.0.0:8080` with `/mcp`, `/health`, and `/events`. |
| `FILE_MCP_ROOT`, `FILE_MCP_AUDIT_LOG`, `FILE_MCP_SERVER_LOG`, `FILE_MCP_SNAPSHOT_DIR` | repo-local defaults | Terraform + `private/env-PREPROD` | Yes | Container storage is rooted under `/workspace`. |
| `FILE_MCP_SERVER_ID`, `FILE_MCP_JOBS_*` | defaults-backed runtime identity and queue settings | Terraform + `private/env-PREPROD` | Yes | Preprod should use a stable server identifier and SQL/Redis jobs backend wiring. |
| `FILE_MCP_ADMIN_UI_ENABLED`, `FILE_MCP_ENDPOINT_HEALTH_CHECK_ALL` | admin enabled, endpoint health enabled in defaults | Terraform + `private/env-PREPROD` | Yes | Preprod keeps admin UI on but limits expensive all-backend checks. |

### Storage backend settings
| Setting(s) | Default / baseline | Preprod source | Preprod change? | Notes |
|---|---|---|---|---|
| `FILE_MCP_STORAGE_BACKEND`, `FILE_MCP_STORAGE_TLS_*` | env-backed defaults | Terraform + `private/env-PREPROD` | Yes | Preprod defaults to `local` but keeps S3/WebDAV/FTP/GDrive credentials ready for operator tests. |
| `FILE_MCP_S3_*` | no committed values | Vault-backed Terraform + `private/env-PREPROD` | Yes | S3 endpoint, region, access key, and secret key come from Vault; bucket name remains environment-specific. |
| `FILE_MCP_WEBDAV_*` | no committed values | Vault-backed Terraform + `private/env-PREPROD` | Yes | Used for remote storage validation. |
| `FILE_MCP_FTP_*` | no committed values | Vault-backed Terraform + `private/env-PREPROD` | Yes | Used for FTP capability tests. |
| `FILE_MCP_GDRIVE_*` | env-backed defaults with optional Vault fallback | Terraform + `private/env-PREPROD` | Yes | OAuth client data is Vault-backed; tokens remain operator-managed if not present in Vault. |

### Auth and TLS settings
| Setting(s) | Default / baseline | Preprod source | Preprod change? | Notes |
|---|---|---|---|---|
| `FILE_MCP_API_KEY_PRIMARY/SECONDARY`, header/scheme | defaults reference env vars | Vault-backed Terraform + `private/env-PREPROD` | Yes | Preprod uses bearer auth. |
| `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `CURL_CA_BUNDLE` | unset | `private/env-PREPROD` | Yes | Host overlay uses system CA bundle; Terraform mounts `/app/certs/trusted-ca-bundle.pem`. |
| `VAULT_ADDR`, `VAULT_MOUNT_POINT`, `VAULT_CONFIG_PATH` | unset | Terraform + `private/env-PREPROD` | Yes | Required to resolve Vault expression-backed defaults during operator runs. |

## 3. Preprod-Specific Overrides
Only settings that differ materially from defaults or that must be supplied for preprod are listed here. The literal operator/test overlay is `/opt/iac/Development/cloud-dog-ai/file-mcp-server/private/env-PREPROD`.

| Override | Why preprod differs | Source of truth |
|---|---|---|
| Streamable HTTP on `8080` | Matches Traefik/public routing. | Terraform 60-container file |
| `/workspace` storage and log paths | Container filesystem replaces repo-local paths. | Terraform 60-container file |
| Bearer API keys | Shared preprod service is protected. | Vault + Terraform |
| Remote storage credentials (S3/WebDAV/FTP/GDrive) | Preprod needs real external storage integrations. | Vault + `private/env-PREPROD` |
| CA bundle and Vault coordinates | Required for shared trust chain and config resolution. | Terraform + `private/env-PREPROD` |

## 4. Vault Configuration
This service reads preprod secrets from the shared Vault config blob at `cloud_dog_ai/config`.

### Required Vault paths
- `dev.services.filemcpserver0` for API keys
- `dev.storage.s3`, `dev.storage.webdav`, `dev.storage.ftp`, `dev.storage.google_drive` for storage backends
- `dev.repository.pypi` for build-time registry credentials

### Operator setup
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
vault kv get -mount=cloud_dog_ai config
```

### Populate or refresh missing entries
Use a merged JSON payload rather than editing Terraform or the running container.

```bash
vault kv put -mount=cloud_dog_ai config   content=@/tmp/cloud-dog-ai-config.preprod.json
```

Example payload fragment:
```json
{
  "dev": {
    "services": {"filemcpserver0": {"api_key": "<API_KEY>"}},
    "storage": {"s3": {"endpoint": "<ENDPOINT>", "access_key_id": "<ACCESS>", "secret_access_key": "<SECRET>"}}
  }
}
```

## 5. Deployment Steps
The project rules forbid ad-hoc `docker build`; use the repo entrypoint script.

1. Load Vault-backed build credentials.
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```
2. Build the image.
```bash
cd /opt/iac/Development/cloud-dog-ai/file-mcp-server && ./docker-build.sh cloud-dog/file-mcp-server:latest
```
3. Tag and push the image.
```bash
docker tag cloud-dog/file-mcp-server:latest registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
docker push registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```
4. Plan and apply the Terraform update from the shared preprod workspace.
```bash
cd '/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/60 Cloud-Dog AI Containers'
terraform plan -out=tfplan.out
terraform apply tfplan.out
```
5. Verify the deployed service.
```bash
curl -fsS https://filemcpserver0.cloud-dog.net/health
```

## 6. Testing Against Preprod
Use the committed tier env file plus `private/env-PREPROD` as the environment-specific overlay.

1. `pytest tests/system --env tests/env-ST --env private/env-PREPROD -q`
2. `pytest tests/integration --env tests/env-IT --env private/env-PREPROD -q`
3. Storage-specific scenarios can add a second overlay such as `private/env-remote-storage`, but `private/env-PREPROD` remains the base preprod layer.

Known limitations:
- Remote storage tests mutate shared external systems; use dedicated test folders/prefixes.
- Google Drive flows may still require operator token refresh if Vault does not store refresh/access tokens.

## 7. Troubleshooting
- `curl -fsS https://filemcpserver0.cloud-dog.net/health` returns a backend-health JSON document.
- `docker -H server0.viewdeck.com logs filemcpserver0.app.vpc0.cloud-dog.net` for runtime logs.
- If S3/WebDAV/FTP probes fail, compare `private/env-PREPROD` against the Vault paths listed above before changing code.
