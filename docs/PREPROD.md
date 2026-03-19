# PREPROD Deployment - file-mcp-server

## 1. Container
- Image: `registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest`
- Hostname: `filemcpserver0.cloud-dog.net`
- Public URL: `https://filemcpserver0.cloud-dog.net`
- Network IP: `10.26.2.66`
- Terraform source: `/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents/filemcpserver_containers.tf.json`

## 2. Ports
| Interface | Internal port | Traefik entrypoint | Public path |
|---|---:|---|---|
| Web | `8080` | `websecure` | `https://filemcpserver0.cloud-dog.net/` |
| MCP | `8080` | `mcpserver` | `https://filemcpserver0.cloud-dog.net/mcp` |
| Health | `8080` | `websecure` | `https://filemcpserver0.cloud-dog.net/health` |

## 3. Volume Mounts
| Container path | Host path | Purpose |
|---|---|---|
| `/app/logs` | `/opt/docker/filemcpserver0/logs` | Logs |
| `/app/certs` | `/opt/docker/filemcpserver0/certificates` | TLS trust bundle |
| `/workspace` | `/opt/docker/filemcpserver0/data/volume1` | Local storage root |

## 4. Environment (Delta from defaults.yaml)
### Runtime
- `FILE_MCP_HTTP_TRANSPORT=streamable-http`
- `FILE_MCP_HTTP_HOST=0.0.0.0`
- `FILE_MCP_HTTP_PORT=8080`
- Base path `/`, MCP path `/mcp`, health path `/health`, stateless mode enabled

### Storage backends
- Local root: `/workspace`
- S3 via `vault.dev.storage.s3.*`
- WebDAV via `vault.dev.storage.webdav.*`
- FTP via `vault.dev.storage.ftp.*`
- Google Drive OAuth via `vault.dev.storage.google_drive.*`

### Auth
- Primary and secondary API key via `vault.dev.services.filemcpserver0.api_key`
- Header contract: `Authorisation: Bearer <token>`
- Admin UI enabled

## 5. External Dependencies
| Dependency | Endpoint | Required |
|---|---|---|
| Vault | `https://vault0.cloud-dog.net` | Y |
| FTP | `ftp.cloud-dog.net:21` | N |
| S3 | `https://storage.cloud-dog.net` | N |
| WebDAV | `https://files.cloud-dog.net` | N |
| Google OAuth | `https://oauth2.googleapis.com/token` | N |

## 6. Health Check
`curl -fsS https://filemcpserver0.cloud-dog.net/health` -> HTTP `200`

## 7. Deployment
Managed by Terraform. Do NOT deploy manually.

## 8. Verification
1. `curl -fsS https://filemcpserver0.cloud-dog.net/health`
2. Open `https://filemcpserver0.cloud-dog.net/`
3. API auth check with file-mcp API key
4. Confirm logs in `/opt/docker/filemcpserver0/logs`

## Vault Gaps
- Optional Google Drive refresh/access tokens are not wired in `private/env-PREPROD`.
