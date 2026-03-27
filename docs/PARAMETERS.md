# Configuration Parameters

All parameters can be set via `defaults.yaml`, `config.yaml`, environment variables, or Vault.

## Server Ports

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| api_server.host | 0.0.0.0 | CLOUD_DOG__API_SERVER__HOST | API server bind address |
| api_server.port | 8060 | CLOUD_DOG__API_SERVER__PORT | API server port |
| api_server.enabled | true | CLOUD_DOG__API_SERVER__ENABLED | Enable API server |
| web_server.host | 0.0.0.0 | CLOUD_DOG__WEB_SERVER__HOST | Web server bind address |
| web_server.port | 8061 | CLOUD_DOG__WEB_SERVER__PORT | Web server port |
| web_server.enabled | true | CLOUD_DOG__WEB_SERVER__ENABLED | Enable web server |
| mcp_server.host | 0.0.0.0 | CLOUD_DOG__MCP_SERVER__HOST | MCP server bind address |
| mcp_server.port | 8062 | CLOUD_DOG__MCP_SERVER__PORT | MCP server port |
| mcp_server.transport | streamable-http | CLOUD_DOG__MCP_SERVER__TRANSPORT | Transport mode |
| mcp_server.enabled | true | CLOUD_DOG__MCP_SERVER__ENABLED | Enable MCP server |
| a2a_server.host | 0.0.0.0 | CLOUD_DOG__A2A_SERVER__HOST | A2A server bind address |
| a2a_server.port | 8063 | CLOUD_DOG__A2A_SERVER__PORT | A2A server port |
| a2a_server.enabled | true | CLOUD_DOG__A2A_SERVER__ENABLED | Enable A2A server |

## HTTP (Legacy Single-Server Mode)

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| http.transport | (empty) | FILE_MCP_HTTP_TRANSPORT | Transport mode |
| http.host | (empty) | FILE_MCP_HTTP_HOST | Bind host |
| http.fallback_host | 127.0.0.1 | FILE_MCP_HTTP_FALLBACK_HOST | Fallback bind host |
| http.port | (empty) | FILE_MCP_HTTP_PORT | Bind port |
| http.base_path | (empty) | FILE_MCP_HTTP_BASE_PATH | Base path prefix |
| http.mcp_path | (empty) | FILE_MCP_HTTP_MCP_PATH | MCP endpoint path |
| http.health_path | (empty) | FILE_MCP_HTTP_HEALTH_PATH | Health endpoint path |
| http.events_path | (empty) | FILE_MCP_HTTP_EVENTS_PATH | Events endpoint path |
| http.stateless_http | (empty) | FILE_MCP_HTTP_STATELESS | Stateless HTTP mode |

## Profile: Authentication

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.server_id | file-mcp-local | FILE_MCP_SERVER_ID | Logical server identifier |
| profiles.default.auth.api_keys | [] | FILE_MCP_API_KEY_PRIMARY | API keys for authentication |
| profiles.default.auth.header_name | (empty) | FILE_MCP_AUTH_HEADER_NAME | Custom auth header name |
| profiles.default.auth.header_scheme | (empty) | FILE_MCP_AUTH_HEADER_SCHEME | Custom auth header scheme |

## Profile: Storage

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.storage.backend | (empty) | FILE_MCP_STORAGE_BACKEND | Storage backend (s3, webdav, ftp, google_drive) |
| profiles.default.storage.tls.insecure_skip_verify | (empty) | FILE_MCP_STORAGE_TLS_INSECURE | Skip TLS verification |
| profiles.default.storage.tls.ca_bundle_path | (empty) | FILE_MCP_STORAGE_TLS_CA_BUNDLE | CA bundle path |

### S3

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.storage.s3.endpoint | (empty) | FILE_MCP_S3_ENDPOINT | S3 endpoint URL |
| profiles.default.storage.s3.bucket | (empty) | FILE_MCP_S3_BUCKET | S3 bucket name |
| profiles.default.storage.s3.region | (empty) | FILE_MCP_S3_REGION | S3 region |
| profiles.default.storage.s3.access_key | (empty) | FILE_MCP_S3_ACCESS_KEY / Vault | S3 access key |
| profiles.default.storage.s3.secret_key | (empty) | FILE_MCP_S3_SECRET_KEY / Vault | S3 secret key |
| profiles.default.storage.s3.prefix | (empty) | FILE_MCP_S3_PREFIX | Key prefix |

### WebDAV

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.storage.webdav.base_url | (empty) | FILE_MCP_WEBDAV_BASE_URL | WebDAV server URL |
| profiles.default.storage.webdav.username | (empty) | FILE_MCP_WEBDAV_USERNAME / Vault | WebDAV username |
| profiles.default.storage.webdav.password | (empty) | FILE_MCP_WEBDAV_PASSWORD / Vault | WebDAV password |
| profiles.default.storage.webdav.move_retry_count | 3 | - | Move operation retries |
| profiles.default.storage.webdav.move_retry_backoff_s | 1.0 | - | Move retry backoff |
| profiles.default.storage.webdav.move_probe_timeout_s | 5 | - | Move probe timeout |
| profiles.default.storage.webdav.move_retry_statuses | 423,502,503,504 | - | Retryable HTTP statuses |

### FTP

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.storage.ftp.host | (empty) | FILE_MCP_FTP_HOST | FTP host |
| profiles.default.storage.ftp.port | (empty) | FILE_MCP_FTP_PORT | FTP port |
| profiles.default.storage.ftp.username | (empty) | FILE_MCP_FTP_USERNAME / Vault | FTP username |
| profiles.default.storage.ftp.password | (empty) | FILE_MCP_FTP_PASSWORD / Vault | FTP password |
| profiles.default.storage.ftp.base_dir | (empty) | FILE_MCP_FTP_BASE_DIR | FTP base directory |
| profiles.default.storage.ftp.use_tls | (empty) | FILE_MCP_FTP_USE_TLS | Enable FTPS |

### Google Drive

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.storage.google_drive.user_email | (empty) | FILE_MCP_GDRIVE_USER_EMAIL | User email |
| profiles.default.storage.google_drive.folder_id | (empty) | FILE_MCP_GDRIVE_FOLDER_ID | Root folder ID |
| profiles.default.storage.google_drive.folder_url | (empty) | FILE_MCP_GDRIVE_FOLDER_URL | Root folder URL |
| profiles.default.storage.google_drive.client_id | (empty) | FILE_MCP_GDRIVE_CLIENT_ID / Vault | OAuth client ID |
| profiles.default.storage.google_drive.client_secret | (empty) | FILE_MCP_GDRIVE_CLIENT_SECRET / Vault | OAuth client secret |
| profiles.default.storage.google_drive.refresh_token | (empty) | FILE_MCP_GDRIVE_REFRESH_TOKEN / Vault | OAuth refresh token |
| profiles.default.storage.google_drive.access_token | (empty) | FILE_MCP_GDRIVE_ACCESS_TOKEN / Vault | OAuth access token |
| profiles.default.storage.google_drive.oauth_scope | https://www.googleapis.com/auth/drive | FILE_MCP_GDRIVE_OAUTH_SCOPE | OAuth scope |
| profiles.default.storage.google_drive.token_uri | (empty) | FILE_MCP_GDRIVE_TOKEN_URI / Vault | OAuth token URI |

## Profile: Scope

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.scope.roots | [] | FILE_MCP_ROOT | Allowed root directories |
| profiles.default.scope.allow_globs | ["**/*"] | - | Allowed file glob patterns |
| profiles.default.scope.deny_globs | ["**/.git/**"] | - | Denied file glob patterns |
| profiles.default.scope.allowed_exts | [] | - | Allowed file extensions (empty = all) |
| profiles.default.scope.read_only_exts | [] | - | Read-only file extensions |

## Profile: Audit & Snapshots

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.audit.log_path | (empty) | FILE_MCP_AUDIT_LOG | Audit log path |
| profiles.default.audit.include_content_hashes | true | - | Hash content in audit |
| profiles.default.snapshots.enabled | false | - | Enable snapshots |
| profiles.default.snapshots.mode | none | - | Snapshot mode |
| profiles.default.snapshots.dir | (empty) | FILE_MCP_SNAPSHOT_DIR | Snapshot directory |
| profiles.default.snapshots.retention_days | 30 | - | Snapshot retention days |

## Profile: Validation & Conversion

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.validation.default_mode | warn | - | Default validation mode |
| profiles.default.validation.per_type | {} | - | Per-type validation modes |
| profiles.default.conversion.enabled | false | - | Enable file conversion |
| profiles.default.conversion.backends | [] | - | Conversion backends |
| profiles.default.conversion.max_input_mb | 25 | - | Max input file size (MB) |

## Profile: Limits

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.limits.search_max_results | 250 | - | Max search results |
| profiles.default.limits.search_max_file_mb | 5 | - | Max file size for search (MB) |
| profiles.default.limits.search_timeout_s | 30 | - | Search timeout (seconds) |
| profiles.default.limits.storage_timeout_s | 30 | - | Storage operation timeout |
| profiles.default.limits.conversion_timeout_s | 60 | - | Conversion timeout |

## Profile: Jobs

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.jobs.enabled | true | FILE_MCP_JOBS_ENABLED | Enable managed jobs |
| profiles.default.jobs.backend | sql | FILE_MCP_JOBS_BACKEND | Jobs backend |
| profiles.default.jobs.queue_name | file-mcp | FILE_MCP_JOBS_QUEUE | Queue name |
| profiles.default.jobs.payload_max_bytes | 65536 | FILE_MCP_JOBS_PAYLOAD_MAX_BYTES | Max job payload size |
| profiles.default.jobs.sql_url | sqlite:///database/file_mcp.db | FILE_MCP_JOBS_SQL_URL | SQL backend URL |
| profiles.default.jobs.redis_url | disabled | FILE_MCP_JOBS_REDIS_URL | Redis backend URL |
| profiles.default.jobs.redis_key_prefix | file_mcp_jobs | FILE_MCP_JOBS_REDIS_KEY_PREFIX | Redis key prefix |

## Profile: Endpoint Health

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.endpoint_health.enabled | true | - | Enable endpoint health monitoring |
| profiles.default.endpoint_health.check_on_startup | true | - | Check health at startup |
| profiles.default.endpoint_health.check_all_configured_backends | true | - | Check all backends |
| profiles.default.endpoint_health.max_retries | 3 | - | Max health check retries |
| profiles.default.endpoint_health.retry_interval_s | 2 | - | Retry interval (seconds) |
| profiles.default.endpoint_health.retry_window_s | 30 | - | Retry window (seconds) |
| profiles.default.endpoint_health.max_failures_before_restart | 5 | - | Failures before restart |
| profiles.default.endpoint_health.recover_after_s | 30 | - | Recovery wait (seconds) |
| profiles.default.endpoint_health.restart_on_threshold | false | - | Auto-restart on threshold |
| profiles.default.endpoint_health.restart_exit_code | 75 | - | Exit code for restart |

## Logging

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| log.service_instance | file-mcp-local | FILE_MCP_SERVER_ID | Service instance ID |
| log.environment | dev | CLOUD_DOG_ENVIRONMENT | Deployment environment |
| log.retention.hot_days | 14 | - | Days to keep hot logs |
| log.retention.cold_days | 60 | - | Days to keep archived logs |
| log.retention.archive_format | gz | - | Archive compression format |
| log.integrity.enabled | true | - | Enable log integrity checks |
| log.integrity.interval_seconds | 300 | - | Integrity check interval |
| log.integrity.hash_algorithm | sha256 | - | Hash algorithm |
| log.rotation.mode | size | - | Rotation mode |
| log.rotation.max_bytes | 104857600 | - | Max bytes before rotation |
| log.rotation.backup_count | 10 | - | Rotated file count |
| log.rotation.compress | true | - | Compress rotated files |
