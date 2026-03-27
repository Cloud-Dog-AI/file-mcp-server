# Environment Reference

This reference is generated from `defaults.yaml` and the standard Cloud-Dog environment override pattern.

## `a2a_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__A2A_SERVER__HOST` | `${CLOUD_DOG__A2A_SERVER__HOST:0.0.0.0}` | Optional | `0.0.0.0` | Host binding or upstream host for a2a server. |
| `CLOUD_DOG__A2A_SERVER__PORT` | `${CLOUD_DOG__A2A_SERVER__PORT:8063}` | Optional | `8080` | Port for a2a server connections. |
| `CLOUD_DOG__A2A_SERVER__ENABLED` | `${CLOUD_DOG__A2A_SERVER__ENABLED:true}` | Optional | `${CLOUD_DOG__A2A_SERVER__ENABLED:true}` | Toggle for a2a server. |

## `api_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__API_SERVER__HOST` | `${CLOUD_DOG__API_SERVER__HOST:0.0.0.0}` | Optional | `0.0.0.0` | Host binding or upstream host for api server. |
| `CLOUD_DOG__API_SERVER__PORT` | `${CLOUD_DOG__API_SERVER__PORT:8060}` | Optional | `8080` | Port for api server connections. |
| `CLOUD_DOG__API_SERVER__ENABLED` | `${CLOUD_DOG__API_SERVER__ENABLED:true}` | Optional | `${CLOUD_DOG__API_SERVER__ENABLED:true}` | Credential or authentication setting for the related subsystem. |

## `http`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__HTTP__TRANSPORT` | `${FILE_MCP_HTTP_TRANSPORT}` | Optional | `${FILE_MCP_HTTP_TRANSPORT}` | Configuration value for http transport. |
| `CLOUD_DOG__HTTP__HOST` | `${FILE_MCP_HTTP_HOST}` | Optional | `0.0.0.0` | Host binding or upstream host for http. |
| `CLOUD_DOG__HTTP__FALLBACK_HOST` | `${FILE_MCP_HTTP_FALLBACK_HOST:127.0.0.1}` | Optional | `${FILE_MCP_HTTP_FALLBACK_HOST:127.0.0.1}` | Host binding or upstream host for http fallback. |
| `CLOUD_DOG__HTTP__PORT` | `${FILE_MCP_HTTP_PORT}` | Optional | `8080` | Port for http connections. |
| `CLOUD_DOG__HTTP__BASE_PATH` | `${FILE_MCP_HTTP_BASE_PATH}` | Optional | `${FILE_MCP_HTTP_BASE_PATH}` | Configuration value for http base path. |
| `CLOUD_DOG__HTTP__MCP_PATH` | `${FILE_MCP_HTTP_MCP_PATH}` | Optional | `${FILE_MCP_HTTP_MCP_PATH}` | Configuration value for http mcp path. |
| `CLOUD_DOG__HTTP__HEALTH_PATH` | `${FILE_MCP_HTTP_HEALTH_PATH}` | Optional | `${FILE_MCP_HTTP_HEALTH_PATH}` | Configuration value for http health path. |
| `CLOUD_DOG__HTTP__EVENTS_PATH` | `${FILE_MCP_HTTP_EVENTS_PATH}` | Optional | `${FILE_MCP_HTTP_EVENTS_PATH}` | Configuration value for http events path. |
| `CLOUD_DOG__HTTP__STATELESS_HTTP` | `${FILE_MCP_HTTP_STATELESS}` | Optional | `${FILE_MCP_HTTP_STATELESS}` | Configuration value for http stateless http. |

## `log`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__LOG__SERVICE_INSTANCE` | `${FILE_MCP_SERVER_ID:file-mcp-local}` | Optional | `${FILE_MCP_SERVER_ID:file-mcp-local}` | Configuration value for log service instance. |
| `CLOUD_DOG__LOG__ENVIRONMENT` | `${CLOUD_DOG_ENVIRONMENT:dev}` | Optional | `${CLOUD_DOG_ENVIRONMENT:dev}` | Configuration value for log environment. |
| `CLOUD_DOG__LOG__RETENTION__HOT_DAYS` | `14` | Optional | `14` | Configuration value for log retention hot days. |
| `CLOUD_DOG__LOG__RETENTION__COLD_DAYS` | `60` | Optional | `60` | Configuration value for log retention cold days. |
| `CLOUD_DOG__LOG__RETENTION__ARCHIVE_FORMAT` | `gz` | Optional | `gz` | Configuration value for log retention archive format. |
| `CLOUD_DOG__LOG__INTEGRITY__ENABLED` | `true` | Optional | `true` | Toggle for log integrity. |
| `CLOUD_DOG__LOG__INTEGRITY__INTERVAL_SECONDS` | `300` | Optional | `300` | Timeout or duration control for log integrity interval. |
| `CLOUD_DOG__LOG__INTEGRITY__LOG_FILE` | `logs/audit-integrity.log` | Optional | `logs/audit-integrity.log` | Configuration value for log integrity log file. |
| `CLOUD_DOG__LOG__INTEGRITY__HASH_ALGORITHM` | `sha256` | Optional | `sha256` | Configuration value for log integrity hash algorithm. |
| `CLOUD_DOG__LOG__ROTATION__MODE` | `size` | Optional | `size` | Configuration value for log rotation mode. |
| `CLOUD_DOG__LOG__ROTATION__MAX_BYTES` | `104857600` | Optional | `104857600` | Configuration value for log rotation max bytes. |
| `CLOUD_DOG__LOG__ROTATION__BACKUP_COUNT` | `10` | Optional | `10` | Configuration value for log rotation backup count. |
| `CLOUD_DOG__LOG__ROTATION__WHEN` | `midnight` | Optional | `midnight` | Configuration value for log rotation when. |
| `CLOUD_DOG__LOG__ROTATION__INTERVAL` | `1` | Optional | `1` | Configuration value for log rotation interval. |
| `CLOUD_DOG__LOG__ROTATION__COMPRESS` | `true` | Optional | `true` | Configuration value for log rotation compress. |

## `mcp_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__MCP_SERVER__HOST` | `${CLOUD_DOG__MCP_SERVER__HOST:0.0.0.0}` | Optional | `0.0.0.0` | Host binding or upstream host for mcp server. |
| `CLOUD_DOG__MCP_SERVER__PORT` | `${CLOUD_DOG__MCP_SERVER__PORT:8062}` | Optional | `8080` | Port for mcp server connections. |
| `CLOUD_DOG__MCP_SERVER__TRANSPORT` | `${CLOUD_DOG__MCP_SERVER__TRANSPORT:streamable-http}` | Optional | `${CLOUD_DOG__MCP_SERVER__TRANSPORT:streamable-http}` | Configuration value for mcp server transport. |
| `CLOUD_DOG__MCP_SERVER__ENABLED` | `${CLOUD_DOG__MCP_SERVER__ENABLED:true}` | Optional | `${CLOUD_DOG__MCP_SERVER__ENABLED:true}` | Toggle for mcp server. |

## `profiles`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__PROFILES__DEFAULT__SERVER_ID` | `${FILE_MCP_SERVER_ID:file-mcp-local}` | Optional | `${FILE_MCP_SERVER_ID:file-mcp-local}` | Configuration value for profiles default server id. |
| `CLOUD_DOG__PROFILES__DEFAULT__AUTH__API_KEYS` | `<secret>` | Deployment dependent | `your-api-key` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__AUTH__HEADER_NAME` | `${FILE_MCP_AUTH_HEADER_NAME}` | Optional | `${FILE_MCP_AUTH_HEADER_NAME}` | Configuration value for profiles default auth header name. |
| `CLOUD_DOG__PROFILES__DEFAULT__AUTH__HEADER_SCHEME` | `${FILE_MCP_AUTH_HEADER_SCHEME}` | Optional | `${FILE_MCP_AUTH_HEADER_SCHEME}` | Configuration value for profiles default auth header scheme. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__BACKEND` | `${FILE_MCP_STORAGE_BACKEND}` | Optional | `${FILE_MCP_STORAGE_BACKEND}` | Configuration value for profiles default storage backend. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__TLS__INSECURE_SKIP_VERIFY` | `${FILE_MCP_STORAGE_TLS_INSECURE}` | Optional | `${FILE_MCP_STORAGE_TLS_INSECURE}` | Configuration value for profiles default storage tls insecure skip verify. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__TLS__CA_BUNDLE_PATH` | `${FILE_MCP_STORAGE_TLS_CA_BUNDLE}` | Optional | `${FILE_MCP_STORAGE_TLS_CA_BUNDLE}` | Configuration value for profiles default storage tls ca bundle path. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__ENDPOINT` | `${FILE_MCP_S3_ENDPOINT}` | Optional | `${FILE_MCP_S3_ENDPOINT}` | Configuration value for profiles default storage s3 endpoint. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__BUCKET` | `${FILE_MCP_S3_BUCKET}` | Optional | `${FILE_MCP_S3_BUCKET}` | Configuration value for profiles default storage s3 bucket. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__REGION` | `${FILE_MCP_S3_REGION}` | Optional | `${FILE_MCP_S3_REGION}` | Configuration value for profiles default storage s3 region. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__ACCESS_KEY` | `${vault.dev.storage.s3.access_key_id || FILE_MCP_S3_ACCESS_KE...` | Optional | `${vault.dev.storage.s3.access_key_id || FILE_MCP_S3_ACCESS_KE...` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__SECRET_KEY` | `<secret>` | Deployment dependent | `your-secret-value` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__PREFIX` | `${FILE_MCP_S3_PREFIX}` | Optional | `${FILE_MCP_S3_PREFIX}` | Configuration value for profiles default storage s3 prefix. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__BASE_URL` | `${FILE_MCP_WEBDAV_BASE_URL}` | Deployment dependent | `${FILE_MCP_WEBDAV_BASE_URL}` | Endpoint or connection URL for profiles default storage webdav base. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__USERNAME` | `${vault.dev.storage.webdav.username || FILE_MCP_WEBDAV_USERNA...` | Optional | `service-admin` | Configuration value for profiles default storage webdav username. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__PASSWORD` | `<secret>` | Deployment dependent | `your-secure-password` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_COUNT` | `3` | Optional | `3` | Configuration value for profiles default storage webdav move retry count. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_BACKOFF_S` | `1.0` | Optional | `1.0` | Configuration value for profiles default storage webdav move retry backoff s. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_PROBE_TIMEOUT_S` | `5` | Optional | `5` | Configuration value for profiles default storage webdav move probe timeout s. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_STATUSES` | `423,502,503,504` | Optional | `423,502,503,504` | Configuration value for profiles default storage webdav move retry statuses. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__HOST` | `${FILE_MCP_FTP_HOST}` | Optional | `0.0.0.0` | Host binding or upstream host for profiles default storage ftp. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__PORT` | `${FILE_MCP_FTP_PORT}` | Optional | `8080` | Port for profiles default storage ftp connections. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__USERNAME` | `${vault.dev.storage.ftp.username || FILE_MCP_FTP_USERNAME || ''}` | Optional | `service-admin` | Configuration value for profiles default storage ftp username. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__PASSWORD` | `<secret>` | Deployment dependent | `your-secure-password` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__BASE_DIR` | `${FILE_MCP_FTP_BASE_DIR}` | Optional | `${FILE_MCP_FTP_BASE_DIR}` | Configuration value for profiles default storage ftp base dir. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__USE_TLS` | `${FILE_MCP_FTP_USE_TLS}` | Optional | `${FILE_MCP_FTP_USE_TLS}` | Configuration value for profiles default storage ftp use tls. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__USER_EMAIL` | `${FILE_MCP_GDRIVE_USER_EMAIL}` | Optional | `${FILE_MCP_GDRIVE_USER_EMAIL}` | Configuration value for profiles default storage google drive user email. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_ID` | `${FILE_MCP_GDRIVE_FOLDER_ID}` | Optional | `${FILE_MCP_GDRIVE_FOLDER_ID}` | Configuration value for profiles default storage google drive folder id. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_URL` | `${FILE_MCP_GDRIVE_FOLDER_URL}` | Deployment dependent | `${FILE_MCP_GDRIVE_FOLDER_URL}` | Endpoint or connection URL for profiles default storage google drive folder. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_URL_EXAMPLE` | `${FILE_MCP_GDRIVE_FOLDER_URL_EXAMPLE:https://drive.google.com...` | Deployment dependent | `${FILE_MCP_GDRIVE_FOLDER_URL_EXAMPLE:https://drive.google.com...` | Configuration value for profiles default storage google drive folder url example. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__CLIENT_ID` | `${vault.dev.storage.google_drive.client_id || FILE_MCP_GDRIVE...` | Optional | `${vault.dev.storage.google_drive.client_id || FILE_MCP_GDRIVE...` | Configuration value for profiles default storage google drive client id. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__CLIENT_SECRET` | `<secret>` | Deployment dependent | `your-secret-value` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__REFRESH_TOKEN` | `<secret>` | Deployment dependent | `your-secret-value` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__ACCESS_TOKEN` | `<secret>` | Deployment dependent | `your-secret-value` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__OAUTH_SCOPE` | `${FILE_MCP_GDRIVE_OAUTH_SCOPE:https://www.googleapis.com/auth...` | Optional | `${FILE_MCP_GDRIVE_OAUTH_SCOPE:https://www.googleapis.com/auth...` | Configuration value for profiles default storage google drive oauth scope. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__OAUTH_AUTHORIZE_URI` | `${FILE_MCP_GDRIVE_AUTHORIZE_URI:https://accounts.google.com/o...` | Deployment dependent | `${FILE_MCP_GDRIVE_AUTHORIZE_URI:https://accounts.google.com/o...` | Endpoint or connection URL for profiles default storage google drive oauth authorize. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__API_BASE_URI` | `${FILE_MCP_GDRIVE_API_BASE_URI:https://www.googleapis.com/dri...` | Deployment dependent | `${FILE_MCP_GDRIVE_API_BASE_URI:https://www.googleapis.com/dri...` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__UPLOAD_BASE_URI` | `${FILE_MCP_GDRIVE_UPLOAD_BASE_URI:https://www.googleapis.com/...` | Deployment dependent | `${FILE_MCP_GDRIVE_UPLOAD_BASE_URI:https://www.googleapis.com/...` | Endpoint or connection URL for profiles default storage google drive upload base. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__REDIRECT_URI` | `${FILE_MCP_GDRIVE_REDIRECT_URI:urn:ietf:wg:oauth:2.0:oob}` | Deployment dependent | `${FILE_MCP_GDRIVE_REDIRECT_URI:urn:ietf:wg:oauth:2.0:oob}` | Endpoint or connection URL for profiles default storage google drive redirect. |
| `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__TOKEN_URI` | `<secret>` | Deployment dependent | `your-secret-value` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ROOTS` | `["${FILE_MCP_ROOT}"]` | Optional | `<set as needed>` | Configuration value for profiles default scope roots. |
| `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ALLOW_GLOBS` | `["**/*"]` | Optional | `<set as needed>` | Configuration value for profiles default scope allow globs. |
| `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__DENY_GLOBS` | `["**/.git/**"]` | Optional | `<set as needed>` | Configuration value for profiles default scope deny globs. |
| `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ALLOWED_EXTS` | `[]` | Optional | `<set as needed>` | Configuration value for profiles default scope allowed exts. |
| `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__READ_ONLY_EXTS` | `[]` | Optional | `<set as needed>` | Configuration value for profiles default scope read only exts. |
| `CLOUD_DOG__PROFILES__DEFAULT__AUDIT__LOG_PATH` | `${FILE_MCP_AUDIT_LOG}` | Optional | `${FILE_MCP_AUDIT_LOG}` | Configuration value for profiles default audit log path. |
| `CLOUD_DOG__PROFILES__DEFAULT__AUDIT__INCLUDE_CONTENT_HASHES` | `true` | Optional | `true` | Configuration value for profiles default audit include content hashes. |
| `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__ENABLED` | `false` | Optional | `false` | Toggle for profiles default snapshots. |
| `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__MODE` | `none` | Optional | `none` | Configuration value for profiles default snapshots mode. |
| `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__DIR` | `${FILE_MCP_SNAPSHOT_DIR}` | Optional | `./data/service.dat` | Configuration value for profiles default snapshots dir. |
| `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__RETENTION_DAYS` | `30` | Optional | `30` | Configuration value for profiles default snapshots retention days. |
| `CLOUD_DOG__PROFILES__DEFAULT__VALIDATION__DEFAULT_MODE` | `warn` | Optional | `warn` | Configuration value for profiles default validation default mode. |
| `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__ENABLED` | `false` | Optional | `false` | Toggle for profiles default conversion. |
| `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__BACKENDS` | `[]` | Optional | `<set as needed>` | Configuration value for profiles default conversion backends. |
| `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__MAX_INPUT_MB` | `25` | Optional | `25` | Configuration value for profiles default conversion max input mb. |
| `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__ENABLED` | `true` | Optional | `true` | Toggle for profiles default observability. |
| `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__LOG_PATH` | `${FILE_MCP_SERVER_LOG}` | Optional | `${FILE_MCP_SERVER_LOG}` | Configuration value for profiles default observability log path. |
| `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__LEVEL` | `INFO` | Optional | `INFO` | Configuration value for profiles default observability level. |
| `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_MAX_RESULTS` | `250` | Optional | `250` | Configuration value for profiles default limits search max results. |
| `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_MAX_FILE_MB` | `5` | Optional | `5` | Configuration value for profiles default limits search max file mb. |
| `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_TIMEOUT_S` | `30` | Optional | `30` | Configuration value for profiles default limits search timeout s. |
| `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__STORAGE_TIMEOUT_S` | `30` | Optional | `30` | Configuration value for profiles default limits storage timeout s. |
| `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__CONVERSION_TIMEOUT_S` | `60` | Optional | `60` | Configuration value for profiles default limits conversion timeout s. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__ENABLED` | `${FILE_MCP_JOBS_ENABLED:true}` | Optional | `${FILE_MCP_JOBS_ENABLED:true}` | Toggle for profiles default jobs. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__BACKEND` | `${FILE_MCP_JOBS_BACKEND:sql}` | Optional | `${FILE_MCP_JOBS_BACKEND:sql}` | Configuration value for profiles default jobs backend. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__QUEUE_NAME` | `${FILE_MCP_JOBS_QUEUE:file-mcp}` | Optional | `${FILE_MCP_JOBS_QUEUE:file-mcp}` | Configuration value for profiles default jobs queue name. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__PAYLOAD_MAX_BYTES` | `${FILE_MCP_JOBS_PAYLOAD_MAX_BYTES:65536}` | Optional | `${FILE_MCP_JOBS_PAYLOAD_MAX_BYTES:65536}` | Configuration value for profiles default jobs payload max bytes. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__SQL_URL` | `${FILE_MCP_JOBS_SQL_URL:sqlite:///database/file_mcp.db}` | Deployment dependent | `${FILE_MCP_JOBS_SQL_URL:sqlite:///database/file_mcp.db}` | Endpoint or connection URL for profiles default jobs sql. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__REDIS_URL` | `${FILE_MCP_JOBS_REDIS_URL:disabled}` | Deployment dependent | `${FILE_MCP_JOBS_REDIS_URL:disabled}` | Endpoint or connection URL for profiles default jobs redis. |
| `CLOUD_DOG__PROFILES__DEFAULT__JOBS__REDIS_KEY_PREFIX` | `${FILE_MCP_JOBS_REDIS_KEY_PREFIX:file_mcp_jobs}` | Optional | `${FILE_MCP_JOBS_REDIS_KEY_PREFIX:file_mcp_jobs}` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__ENABLED` | `true` | Optional | `true` | Toggle for profiles default endpoint health. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__CHECK_ON_STARTUP` | `true` | Optional | `true` | Configuration value for profiles default endpoint health check on startup. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__CHECK_ALL_CONFIGURED_BACKENDS` | `true` | Optional | `true` | Configuration value for profiles default endpoint health check all configured backends. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__MAX_RETRIES` | `3` | Optional | `3` | Configuration value for profiles default endpoint health max retries. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RETRY_INTERVAL_S` | `2` | Optional | `2` | Configuration value for profiles default endpoint health retry interval s. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RETRY_WINDOW_S` | `30` | Optional | `30` | Configuration value for profiles default endpoint health retry window s. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__MAX_FAILURES_BEFORE_RESTART` | `5` | Optional | `5` | Configuration value for profiles default endpoint health max failures before restart. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RECOVER_AFTER_S` | `30` | Optional | `30` | Configuration value for profiles default endpoint health recover after s. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RESTART_ON_THRESHOLD` | `false` | Optional | `false` | Configuration value for profiles default endpoint health restart on threshold. |
| `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RESTART_EXIT_CODE` | `75` | Optional | `75` | Configuration value for profiles default endpoint health restart exit code. |

## `web_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__WEB_SERVER__HOST` | `${CLOUD_DOG__WEB_SERVER__HOST:0.0.0.0}` | Optional | `0.0.0.0` | Host binding or upstream host for web server. |
| `CLOUD_DOG__WEB_SERVER__PORT` | `${CLOUD_DOG__WEB_SERVER__PORT:8061}` | Optional | `8080` | Port for web server connections. |
| `CLOUD_DOG__WEB_SERVER__ENABLED` | `${CLOUD_DOG__WEB_SERVER__ENABLED:true}` | Optional | `${CLOUD_DOG__WEB_SERVER__ENABLED:true}` | Toggle for web server. |

## Vault Support

| Variable | Purpose | Example |
|----------|---------|---------|
| `VAULT_ADDR` | Vault server URL when using secret-backed config resolution. | `https://your-vault-server` |
| `VAULT_TOKEN` | Token-based authentication for Vault when applicable. | `your-vault-token` |
| `VAULT_MOUNT_POINT` | Secret mount used by your Vault deployment. | `secret` |
| `VAULT_CONFIG_PATH` | Config path holding service settings. | `services/your-service` |
