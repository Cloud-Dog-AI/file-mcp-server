# file-mcp-server Environment Reference

## 1. Configuration Precedence

`file-mcp-server` resolves configuration in this order:

1. `os.environ`
2. `--env` file(s)
3. `config.yaml`
4. `defaults.yaml`
5. Vault expressions resolved by `cloud_dog_config`

## 2. Core Runtime Variables

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_API_KEY_PRIMARY` | Primary API key for profile auth | none | Yes | `secret` |
| `FILE_MCP_API_KEY_SECONDARY` | Secondary API key (rotation/testing) | empty | No | `12345678` |
| `FILE_MCP_AUTH_HEADER_NAME` | Auth header name | `Authorization` | Yes | `Authorization` |
| `FILE_MCP_AUTH_HEADER_SCHEME` | Auth scheme | `Bearer` | Yes | `Bearer` |
| `FILE_MCP_ROOT` | Scope root path | none | Yes | `.` |
| `FILE_MCP_AUDIT_LOG` | Audit JSONL output path | none | Yes | `./working/test-env-ut/audit.log.jsonl` |
| `FILE_MCP_SERVER_LOG` | Server log path | none | Yes | `./working/test-env-ut/server.log` |
| `FILE_MCP_SNAPSHOT_DIR` | Snapshot directory path | none | Yes | `./working/test-env-ut/snapshots` |
| `FILE_MCP_STORAGE_BACKEND` | Active storage backend | `local` | Yes | `local` |
| `FILE_MCP_STORAGE_TIMEOUT_S` | Storage operation timeout (seconds) | `30` | No | `30` |
| `FILE_MCP_STORAGE_TLS_INSECURE` | Skip TLS verification for remote backends | `false` | No | `false` |
| `FILE_MCP_STORAGE_TLS_CA_BUNDLE` | CA bundle path for backend TLS | empty | No | `/app/certs/ca.crt` |
| `FILE_MCP_SEARCH_MAX_RESULTS` | Search result cap | `250` | No | `250` |
| `FILE_MCP_SEARCH_MAX_FILE_MB` | Maximum file size for search | `5` | No | `5` |
| `FILE_MCP_SEARCH_TIMEOUT_S` | Search timeout (seconds) | `30` | No | `30` |
| `FILE_MCP_CONVERSION_TIMEOUT_S` | Convert timeout (seconds) | `60` | No | `60` |
| `FILE_MCP_CONVERSION_MAX_INPUT_MB` | Convert input max size (MB) | `25` | No | `25` |

## 3. HTTP Transport Variables

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_HTTP_TRANSPORT` | Transport mode (`streamable-http`, `http`, `sse`) | `streamable-http` | Yes | `streamable-http` |
| `FILE_MCP_HTTP_HOST` | Bind host | `127.0.0.1` | Yes | `127.0.0.1` |
| `FILE_MCP_HTTP_PORT` | Bind port | `38190` | Yes | `38190` |
| `FILE_MCP_HTTP_BASE_PATH` | Base path prefix | `/app/v1` | Yes | `/app/v1` |
| `FILE_MCP_HTTP_MCP_PATH` | MCP path | `/mcp` | Yes | `/mcp` |
| `FILE_MCP_HTTP_HEALTH_PATH` | Health path | `/health` | Yes | `/health` |
| `FILE_MCP_HTTP_EVENTS_PATH` | SSE events path | `/events` | Yes | `/events` |
| `FILE_MCP_HTTP_STATELESS` | Stateless HTTP toggle | `true` | No | `true` |
| `FILE_MCP_HTTP_ENABLE_LEGACY_API_ALIAS` | Legacy alias exposure toggle | `true` | No | `true` |

## 4. Storage Backend Variables

### 4.1 S3

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_S3_ENDPOINT` | S3 endpoint URL | empty | For S3 backend | `https://s3.example.com` |
| `FILE_MCP_S3_BUCKET` | S3 bucket | empty | For S3 backend | `test` |
| `FILE_MCP_S3_REGION` | S3 region | empty | For S3 backend | `us-east-1` |
| `FILE_MCP_S3_ACCESS_KEY` | S3 access key | Vault fallback | For S3 backend | `${vault.dev.storage.s3.access_key_id}` |
| `FILE_MCP_S3_SECRET_KEY` | S3 secret key | Vault fallback | For S3 backend | `${vault.dev.storage.s3.secret_access_key}` |
| `FILE_MCP_S3_PREFIX` | Key prefix root | empty | No | `project-a/` |

### 4.2 WebDAV

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_WEBDAV_BASE_URL` | WebDAV base URL | empty | For WebDAV backend | `https://webdav.example.com/remote.php/dav/files/user` |
| `FILE_MCP_WEBDAV_USERNAME` | WebDAV username | Vault fallback | For WebDAV backend | `${vault.dev.storage.webdav.username}` |
| `FILE_MCP_WEBDAV_PASSWORD` | WebDAV password | Vault fallback | For WebDAV backend | `${vault.dev.storage.webdav.password}` |

### 4.3 FTP

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_FTP_HOST` | FTP host | `localhost` | For FTP backend | `${vault.dev.storage.ftp.host}` |
| `FILE_MCP_FTP_PORT` | FTP port | `21` | For FTP backend | `${vault.dev.storage.ftp.port}` |
| `FILE_MCP_FTP_USERNAME` | FTP username | Vault fallback | For FTP backend | `${vault.dev.storage.ftp.username}` |
| `FILE_MCP_FTP_PASSWORD` | FTP password | Vault fallback | For FTP backend | `${vault.dev.storage.ftp.password}` |
| `FILE_MCP_FTP_BASE_DIR` | FTP base directory | `/` | No | `/` |
| `FILE_MCP_FTP_USE_TLS` | FTP TLS toggle | `false` | No | `false` |

### 4.4 Google Drive

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `FILE_MCP_GDRIVE_CLIENT_ID` | OAuth client id | Vault fallback | For Google Drive backend | `${vault.dev.storage.google_drive.client_id}` |
| `FILE_MCP_GDRIVE_CLIENT_SECRET` | OAuth client secret | Vault fallback | For Google Drive backend | `${vault.dev.storage.google_drive.client_secret}` |
| `FILE_MCP_GDRIVE_USER_EMAIL` | Google account email | empty | No | `user@example.com` |
| `FILE_MCP_GDRIVE_FOLDER_ID` | Target folder id | empty | Folder id or URL required | `abc123...` |
| `FILE_MCP_GDRIVE_FOLDER_URL` | Target folder URL | empty | Folder id or URL required | `https://drive.google.com/drive/folders/...` |
| `FILE_MCP_GDRIVE_REFRESH_TOKEN` | OAuth refresh token | empty | For live access | `<token>` |
| `FILE_MCP_GDRIVE_ACCESS_TOKEN` | OAuth access token | empty | No (refresh path preferred) | `<token>` |
| `FILE_MCP_GDRIVE_REDIRECT_URI` | OAuth redirect URI | `urn:ietf:wg:oauth:2.0:oob` | No | `https://filemcpserver0.cloud-dog.net/admin/google-drive/callback` |
| `FILE_MCP_GDRIVE_TOKEN_URI` | OAuth token endpoint | `https://oauth2.googleapis.com/token` | No | `${vault.dev.storage.google_drive.token_uri}` |
| `FILE_MCP_GDRIVE_AUTH_CODE` | One-time auth code | empty | Setup-time only | `<code>` |

## 5. Database Variables

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CLOUD_DOG__DB__URL` / `CLOUD_DOG_DB__URL` / `FILE_MCP_DB_URL` | Full DB URL override | none | Optional | `postgresql+psycopg://user:pass@host:5432/db` |
| `CLOUD_DOG_DB__DIALECT` / `CLOUD_DOG__DB__DIALECT` | DB dialect | `sqlite` | No | `sqlite`, `mysql`, `postgresql` |
| `CLOUD_DOG_DB__HOST` / `CLOUD_DOG__DB__HOST` | DB host | none | For MySQL/PostgreSQL | `${vault.dev.databases.filemcp_dev_postgresql.server}` |
| `CLOUD_DOG_DB__PORT` / `CLOUD_DOG__DB__PORT` | DB port | none | For MySQL/PostgreSQL | `5432` |
| `CLOUD_DOG_DB__USERNAME` / `CLOUD_DOG__DB__USERNAME` | DB username | none | For MySQL/PostgreSQL | `${vault.dev.databases.filemcp_dev_postgresql.username}` |
| `CLOUD_DOG_DB__PASSWORD` / `CLOUD_DOG__DB__PASSWORD` | DB password | none | For MySQL/PostgreSQL | `${vault.dev.databases.filemcp_dev_postgresql.password}` |
| `CLOUD_DOG_DB__DATABASE` / `CLOUD_DOG__DB__DATABASE` | DB name or SQLite file path | `./database/file_mcp.db` | Yes | `./database/file_mcp.db` |
| `CLOUD_DOG_DB__PATH` / `CLOUD_DOG__DB__PATH` | DB path override | none | No | `./database/file_mcp.db` |
| `CLOUD_DOG_DB__SCHEMA` / `CLOUD_DOG__DB__SCHEMA` | Schema name | none | No | `public` |

## 6. Test-only and Harness Variables

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `TEST_ENV_TIER` | Tier marker (`QT`, `UT`, `ST`, `IT`, `AT`) | none | Yes in env files | `UT` |
| `TEST_API_BASE_PATH` | Test API base path | `/app/v1` | Yes in env files | `/app/v1` |
| `TEST_MCP_BASE_PATH` | Test MCP path | `/mcp` | Yes in env files | `/mcp` |
| `TEST_WEB_BASE_PATH` | Test web base path | `/` | Yes in env files | `/` |
| `TEST_A2A_BASE_PATH` | Test A2A base path | `/a2a` | Yes in env files | `/a2a` |
| `TEST_API_KEY` | Preprod API key for AT harness | empty | Preprod AT only | `<api-key>` |
| `TEST_A2A_API_KEY` | A2A test key | empty | A2A test flows | `12345678` |
| `FILE_MCP_RUN_DOCKER_TESTS` | Enable docker integration tests | `0` | No | `1` |
| `FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS` | Enable docker remote storage matrix | `0` | No | `1` |
| `FILE_MCP_RUN_DOCKER_BRIDGE_TESTS` | Enable docker bridge tests | `0` | No | `1` |
| `FILE_MCP_STRICT_REMOTE_TESTS` | Enable strict remote backend tests | `0` | No | `1` |
| `FILE_MCP_RUN_REMOTE_MATRIX_TESTS` | Enable remote backend matrix | `0` | No | `1` |
| `FILE_MCP_RUN_GOOGLE_LIVE_TESTS` | Enable live Google tests | `0` | No | `1` |
| `FILE_MCP_RUN_GDRIVE_LIVE_TEST` | Enable live Google Drive IT | `0` | No | `1` |
| `FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST` | Enable live OAuth AT | `0` | No | `1` |

### Local docker controller envs

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `LOCAL_DOCKER_SOURCE_ENV` | Source env file for local docker helper | none | Yes for helper | `tests/env-IT-local-docker` |
| `LOCAL_DOCKER_COMPOSE_FILE` | Compose file path | `docker-compose.local.yml` | No | `docker-compose.local.yml` |
| `LOCAL_DOCKER_PROJECT_NAME` | Compose project name | helper default | No | `file-mcp-local-docker` |
| `LOCAL_DOCKER_SERVICES` | Service list | helper default | No | `file-mcp` |

## 7. Vault Integration

Load Vault credentials before IT/AT runs:

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
bash scripts/validate-vault.sh
```

Key runtime Vault variables:
- `VAULT_ADDR`
- `VAULT_TOKEN`
- `VAULT_MOUNT_POINT`
- `VAULT_CONFIG_PATH`

## 8. Example Configurations

### Local dev (SQLite, local backend)

```bash
./server_control.sh --env tests/env-UT serve
```

### Docker (remote backends + Vault)

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
./docker-build.sh registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
docker compose -f docker-compose.local.yml --env-file tests/env-IT-local-docker up -d
```

### Preprod profile-chain validation

```bash
.venv/bin/python -m pytest tests/application --env tests/env-AT-preprod -q
```

## 9. Full Variable Index (tests/env-*)

The following variables are present across committed tier env files and overlays:

```text
CLOUD_DOG_DB__DATABASE
CLOUD_DOG_DB__DIALECT
CLOUD_DOG_DB__HOST
CLOUD_DOG_DB__PASSWORD
CLOUD_DOG_DB__PORT
CLOUD_DOG_DB__USERNAME
CLOUD_DOG__DB__DATABASE
CLOUD_DOG__DB__DIALECT
FILE_MCP_API_KEY_PRIMARY
FILE_MCP_API_KEY_SECONDARY
FILE_MCP_AUDIT_LOG
FILE_MCP_AUTH_HEADER_NAME
FILE_MCP_AUTH_HEADER_SCHEME
FILE_MCP_CONVERSION_MAX_INPUT_MB
FILE_MCP_CONVERSION_TIMEOUT_S
FILE_MCP_DOCKER_TEST_IMAGE
FILE_MCP_FTP_BASE_DIR
FILE_MCP_FTP_HOST
FILE_MCP_FTP_PASSWORD
FILE_MCP_FTP_PORT
FILE_MCP_FTP_USERNAME
FILE_MCP_FTP_USE_TLS
FILE_MCP_GDRIVE_ACCESS_TOKEN
FILE_MCP_GDRIVE_AUTH_CODE
FILE_MCP_GDRIVE_CLIENT_ID
FILE_MCP_GDRIVE_CLIENT_SECRET
FILE_MCP_GDRIVE_FOLDER_ID
FILE_MCP_GDRIVE_FOLDER_URL
FILE_MCP_GDRIVE_REDIRECT_URI
FILE_MCP_GDRIVE_REFRESH_TOKEN
FILE_MCP_GDRIVE_TOKEN_URI
FILE_MCP_GDRIVE_USER_EMAIL
FILE_MCP_HTTP_BASE_PATH
FILE_MCP_HTTP_EVENTS_PATH
FILE_MCP_HTTP_HEALTH_PATH
FILE_MCP_HTTP_HOST
FILE_MCP_HTTP_MCP_PATH
FILE_MCP_HTTP_PORT
FILE_MCP_HTTP_STATELESS
FILE_MCP_HTTP_TRANSPORT
FILE_MCP_PREPROD_KEY_FTP
FILE_MCP_PREPROD_KEY_LOCAL
FILE_MCP_PREPROD_KEY_S3
FILE_MCP_PREPROD_KEY_WEBDAV
FILE_MCP_PREPROD_PROFILE_FTP
FILE_MCP_PREPROD_PROFILE_LOCAL
FILE_MCP_PREPROD_PROFILE_S3
FILE_MCP_PREPROD_PROFILE_WEBDAV
FILE_MCP_PREPROD_URL
FILE_MCP_ROOT
FILE_MCP_RUN_DOCKER_BRIDGE_TESTS
FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS
FILE_MCP_RUN_DOCKER_TESTS
FILE_MCP_RUN_GDRIVE_LIVE_TEST
FILE_MCP_RUN_GOOGLE_LIVE_TESTS
FILE_MCP_RUN_GOOGLE_OAUTH_LIVE_TEST
FILE_MCP_RUN_PREPROD_AT
FILE_MCP_RUN_REMOTE_MATRIX_TESTS
FILE_MCP_S3_ACCESS_KEY
FILE_MCP_S3_BUCKET
FILE_MCP_S3_ENDPOINT
FILE_MCP_S3_PREFIX
FILE_MCP_S3_REGION
FILE_MCP_S3_SECRET_KEY
FILE_MCP_SEARCH_MAX_FILE_MB
FILE_MCP_SEARCH_MAX_RESULTS
FILE_MCP_SEARCH_TIMEOUT_S
FILE_MCP_SERVER_LOG
FILE_MCP_SNAPSHOT_DIR
FILE_MCP_SNAPSHOT_MAX_STORAGE_MB
FILE_MCP_SNAPSHOT_RETENTION_COUNT
FILE_MCP_SNAPSHOT_RETENTION_DAYS
FILE_MCP_STORAGE_BACKEND
FILE_MCP_STORAGE_TIMEOUT_S
FILE_MCP_STORAGE_TLS_CA_BUNDLE
FILE_MCP_STORAGE_TLS_INSECURE
FILE_MCP_STRICT_REMOTE_TESTS
FILE_MCP_WEBDAV_BASE_URL
FILE_MCP_WEBDAV_PASSWORD
FILE_MCP_WEBDAV_USERNAME
LOCAL_DOCKER_COMPOSE_FILE
LOCAL_DOCKER_PROJECT_NAME
LOCAL_DOCKER_SERVICES
LOCAL_DOCKER_SOURCE_ENV
TEST_A2A_API_KEY
TEST_A2A_BASE_PATH
TEST_API_BASE_PATH
TEST_API_KEY
TEST_BASE_URL
TEST_ENV_TIER
TEST_MCP_BASE_PATH
TEST_MCP_URL
TEST_WEB_BASE_PATH
```
