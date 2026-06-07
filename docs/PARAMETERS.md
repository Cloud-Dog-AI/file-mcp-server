# Parameters

This reference is generated from `defaults.yaml`. Each key can be overridden by the corresponding environment variable.

## `a2a_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `a2a_server.host` | `${CLOUD_DOG__A2A_SERVER__HOST:0.0.0.0}` | `CLOUD_DOG__A2A_SERVER__HOST` | Host binding or upstream host for a2a server. |
| `a2a_server.port` | `${CLOUD_DOG__A2A_SERVER__PORT:8063}` | `CLOUD_DOG__A2A_SERVER__PORT` | Port for a2a server connections. |
| `a2a_server.enabled` | `${CLOUD_DOG__A2A_SERVER__ENABLED:true}` | `CLOUD_DOG__A2A_SERVER__ENABLED` | Toggle for a2a server. |

## `api_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `api_server.host` | `${CLOUD_DOG__API_SERVER__HOST:0.0.0.0}` | `CLOUD_DOG__API_SERVER__HOST` | Host binding or upstream host for api server. |
| `api_server.port` | `${CLOUD_DOG__API_SERVER__PORT:8060}` | `CLOUD_DOG__API_SERVER__PORT` | Port for api server connections. |
| `api_server.enabled` | `${CLOUD_DOG__API_SERVER__ENABLED:true}` | `CLOUD_DOG__API_SERVER__ENABLED` | Credential or authentication setting for the related subsystem. |

## `http`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `http.transport` | `${FILE_MCP_HTTP_TRANSPORT}` | `CLOUD_DOG__HTTP__TRANSPORT` | Configuration value for http transport. |
| `http.host` | `${FILE_MCP_HTTP_HOST}` | `CLOUD_DOG__HTTP__HOST` | Host binding or upstream host for http. |
| `http.fallback_host` | `${FILE_MCP_HTTP_FALLBACK_HOST:127.0.0.1}` | `CLOUD_DOG__HTTP__FALLBACK_HOST` | Host binding or upstream host for http fallback. |
| `http.port` | `${FILE_MCP_HTTP_PORT}` | `CLOUD_DOG__HTTP__PORT` | Port for http connections. |
| `http.base_path` | `${FILE_MCP_HTTP_BASE_PATH}` | `CLOUD_DOG__HTTP__BASE_PATH` | Configuration value for http base path. |
| `http.mcp_path` | `${FILE_MCP_HTTP_MCP_PATH}` | `CLOUD_DOG__HTTP__MCP_PATH` | Configuration value for http mcp path. |
| `http.health_path` | `${FILE_MCP_HTTP_HEALTH_PATH}` | `CLOUD_DOG__HTTP__HEALTH_PATH` | Configuration value for http health path. |
| `http.events_path` | `${FILE_MCP_HTTP_EVENTS_PATH}` | `CLOUD_DOG__HTTP__EVENTS_PATH` | Configuration value for http events path. |
| `http.stateless_http` | `${FILE_MCP_HTTP_STATELESS}` | `CLOUD_DOG__HTTP__STATELESS_HTTP` | Configuration value for http stateless http. |

## `log`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `log.service_instance` | `${FILE_MCP_SERVER_ID:file-mcp-local}` | `CLOUD_DOG__LOG__SERVICE_INSTANCE` | Configuration value for log service instance. |
| `log.environment` | `${CLOUD_DOG_ENVIRONMENT:dev}` | `CLOUD_DOG__LOG__ENVIRONMENT` | Configuration value for log environment. |
| `log.api_server_log` | `logs/api_server.log` | `CLOUD_DOG__LOG__API_SERVER_LOG` | Log file path for the API server role. |
| `log.web_server_log` | `logs/web_server.log` | `CLOUD_DOG__LOG__WEB_SERVER_LOG` | Log file path for the web server role. |
| `log.mcp_server_log` | `logs/mcp_server.log` | `CLOUD_DOG__LOG__MCP_SERVER_LOG` | Log file path for the MCP server role. |
| `log.a2a_server_log` | `logs/a2a_server.log` | `CLOUD_DOG__LOG__A2A_SERVER_LOG` | Log file path for the A2A server role. |
| `log.audit_log` | `logs/audit.log.jsonl` | `CLOUD_DOG__LOG__AUDIT_LOG` | Path for the structured audit log (JSONL). |
| `log.retention.hot_days` | `14` | `CLOUD_DOG__LOG__RETENTION__HOT_DAYS` | Configuration value for log retention hot days. |
| `log.retention.cold_days` | `60` | `CLOUD_DOG__LOG__RETENTION__COLD_DAYS` | Configuration value for log retention cold days. |
| `log.retention.archive_format` | `gz` | `CLOUD_DOG__LOG__RETENTION__ARCHIVE_FORMAT` | Configuration value for log retention archive format. |
| `log.integrity.enabled` | `true` | `CLOUD_DOG__LOG__INTEGRITY__ENABLED` | Toggle for log integrity. |
| `log.integrity.interval_seconds` | `300` | `CLOUD_DOG__LOG__INTEGRITY__INTERVAL_SECONDS` | Timeout or duration control for log integrity interval. |
| `log.integrity.log_file` | `logs/audit-integrity.log` | `CLOUD_DOG__LOG__INTEGRITY__LOG_FILE` | Configuration value for log integrity log file. |
| `log.integrity.hash_algorithm` | `sha256` | `CLOUD_DOG__LOG__INTEGRITY__HASH_ALGORITHM` | Configuration value for log integrity hash algorithm. |
| `log.rotation.mode` | `size` | `CLOUD_DOG__LOG__ROTATION__MODE` | Configuration value for log rotation mode. |
| `log.rotation.max_bytes` | `104857600` | `CLOUD_DOG__LOG__ROTATION__MAX_BYTES` | Configuration value for log rotation max bytes. |
| `log.rotation.backup_count` | `10` | `CLOUD_DOG__LOG__ROTATION__BACKUP_COUNT` | Configuration value for log rotation backup count. |
| `log.rotation.when` | `midnight` | `CLOUD_DOG__LOG__ROTATION__WHEN` | Configuration value for log rotation when. |
| `log.rotation.interval` | `1` | `CLOUD_DOG__LOG__ROTATION__INTERVAL` | Configuration value for log rotation interval. |
| `log.rotation.compress` | `true` | `CLOUD_DOG__LOG__ROTATION__COMPRESS` | Configuration value for log rotation compress. |

## `mcp_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `mcp_server.host` | `${CLOUD_DOG__MCP_SERVER__HOST:0.0.0.0}` | `CLOUD_DOG__MCP_SERVER__HOST` | Host binding or upstream host for mcp server. |
| `mcp_server.port` | `${CLOUD_DOG__MCP_SERVER__PORT:8062}` | `CLOUD_DOG__MCP_SERVER__PORT` | Port for mcp server connections. |
| `mcp_server.transport` | `${CLOUD_DOG__MCP_SERVER__TRANSPORT:streamable-http}` | `CLOUD_DOG__MCP_SERVER__TRANSPORT` | Configuration value for mcp server transport. |
| `mcp_server.enabled` | `${CLOUD_DOG__MCP_SERVER__ENABLED:true}` | `CLOUD_DOG__MCP_SERVER__ENABLED` | Toggle for mcp server. |

## `profiles`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `profiles.default.server_id` | `${FILE_MCP_SERVER_ID:file-mcp-local}` | `CLOUD_DOG__PROFILES__DEFAULT__SERVER_ID` | Configuration value for profiles default server id. |
| `profiles.default.auth.api_keys` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__AUTH__API_KEYS` | Credential or authentication setting for the related subsystem. |
| `profiles.default.auth.header_name` | `${FILE_MCP_AUTH_HEADER_NAME}` | `CLOUD_DOG__PROFILES__DEFAULT__AUTH__HEADER_NAME` | Configuration value for profiles default auth header name. |
| `profiles.default.auth.header_scheme` | `${FILE_MCP_AUTH_HEADER_SCHEME}` | `CLOUD_DOG__PROFILES__DEFAULT__AUTH__HEADER_SCHEME` | Configuration value for profiles default auth header scheme. |
| `profiles.default.storage.backend` | `${FILE_MCP_STORAGE_BACKEND}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__BACKEND` | Configuration value for profiles default storage backend. |
| `profiles.default.storage.tls.insecure_skip_verify` | `${FILE_MCP_STORAGE_TLS_INSECURE}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__TLS__INSECURE_SKIP_VERIFY` | Configuration value for profiles default storage tls insecure skip verify. |
| `profiles.default.storage.tls.ca_bundle_path` | `${FILE_MCP_STORAGE_TLS_CA_BUNDLE}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__TLS__CA_BUNDLE_PATH` | Configuration value for profiles default storage tls ca bundle path. |
| `profiles.default.storage.s3.endpoint` | `${FILE_MCP_S3_ENDPOINT}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__ENDPOINT` | Configuration value for profiles default storage s3 endpoint. |
| `profiles.default.storage.s3.bucket` | `${FILE_MCP_S3_BUCKET}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__BUCKET` | Configuration value for profiles default storage s3 bucket. |
| `profiles.default.storage.s3.region` | `${FILE_MCP_S3_REGION}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__REGION` | Configuration value for profiles default storage s3 region. |
| `profiles.default.storage.s3.access_key` | `${FILE_MCP_S3_ACCESS_KEY}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__ACCESS_KEY` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.s3.secret_key` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__SECRET_KEY` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.s3.prefix` | `${FILE_MCP_S3_PREFIX}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__S3__PREFIX` | Configuration value for profiles default storage s3 prefix. |
| `profiles.default.storage.webdav.base_url` | `${FILE_MCP_WEBDAV_BASE_URL}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__BASE_URL` | Endpoint or connection URL for profiles default storage webdav base. |
| `profiles.default.storage.webdav.username` | `${FILE_MCP_WEBDAV_USERNAME}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__USERNAME` | Configuration value for profiles default storage webdav username. |
| `profiles.default.storage.webdav.password` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__PASSWORD` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.webdav.move_retry_count` | `3` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_COUNT` | Configuration value for profiles default storage webdav move retry count. |
| `profiles.default.storage.webdav.move_retry_backoff_s` | `1.0` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_BACKOFF_S` | Configuration value for profiles default storage webdav move retry backoff s. |
| `profiles.default.storage.webdav.move_probe_timeout_s` | `5` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_PROBE_TIMEOUT_S` | Configuration value for profiles default storage webdav move probe timeout s. |
| `profiles.default.storage.webdav.move_retry_statuses` | `423,502,503,504` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__WEBDAV__MOVE_RETRY_STATUSES` | Configuration value for profiles default storage webdav move retry statuses. |
| `profiles.default.storage.ftp.host` | `${FILE_MCP_FTP_HOST}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__HOST` | Host binding or upstream host for profiles default storage ftp. |
| `profiles.default.storage.ftp.port` | `${FILE_MCP_FTP_PORT}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__PORT` | Port for profiles default storage ftp connections. |
| `profiles.default.storage.ftp.username` | `${FILE_MCP_FTP_USERNAME}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__USERNAME` | Configuration value for profiles default storage ftp username. |
| `profiles.default.storage.ftp.password` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__PASSWORD` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.ftp.base_dir` | `${FILE_MCP_FTP_BASE_DIR}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__BASE_DIR` | Configuration value for profiles default storage ftp base dir. |
| `profiles.default.storage.ftp.use_tls` | `${FILE_MCP_FTP_USE_TLS}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__FTP__USE_TLS` | Configuration value for profiles default storage ftp use tls. |
| `profiles.default.storage.google_drive.user_email` | `${FILE_MCP_GDRIVE_USER_EMAIL}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__USER_EMAIL` | Configuration value for profiles default storage google drive user email. |
| `profiles.default.storage.google_drive.folder_id` | `${FILE_MCP_GDRIVE_FOLDER_ID}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_ID` | Configuration value for profiles default storage google drive folder id. |
| `profiles.default.storage.google_drive.folder_url` | `${FILE_MCP_GDRIVE_FOLDER_URL}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_URL` | Endpoint or connection URL for profiles default storage google drive folder. |
| `profiles.default.storage.google_drive.folder_url_example` | `${FILE_MCP_GDRIVE_FOLDER_URL_EXAMPLE:https://drive.google.com...` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__FOLDER_URL_EXAMPLE` | Configuration value for profiles default storage google drive folder url example. |
| `profiles.default.storage.google_drive.client_id` | `${FILE_MCP_GDRIVE_CLIENT_ID}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__CLIENT_ID` | Configuration value for profiles default storage google drive client id. |
| `profiles.default.storage.google_drive.client_secret` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__CLIENT_SECRET` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.google_drive.refresh_token` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__REFRESH_TOKEN` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.google_drive.access_token` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__ACCESS_TOKEN` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.google_drive.oauth_scope` | `${FILE_MCP_GDRIVE_OAUTH_SCOPE:https://www.googleapis.com/auth...` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__OAUTH_SCOPE` | Configuration value for profiles default storage google drive oauth scope. |
| `profiles.default.storage.google_drive.oauth_authorize_uri` | `${FILE_MCP_GDRIVE_AUTHORIZE_URI:https://accounts.google.com/o...` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__OAUTH_AUTHORIZE_URI` | Endpoint or connection URL for profiles default storage google drive oauth authorize. |
| `profiles.default.storage.google_drive.api_base_uri` | `${FILE_MCP_GDRIVE_API_BASE_URI:https://www.googleapis.com/dri...` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__API_BASE_URI` | Credential or authentication setting for the related subsystem. |
| `profiles.default.storage.google_drive.upload_base_uri` | `${FILE_MCP_GDRIVE_UPLOAD_BASE_URI:https://www.googleapis.com/...` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__UPLOAD_BASE_URI` | Endpoint or connection URL for profiles default storage google drive upload base. |
| `profiles.default.storage.google_drive.redirect_uri` | `${FILE_MCP_GDRIVE_REDIRECT_URI:urn:ietf:wg:oauth:2.0:oob}` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__REDIRECT_URI` | Endpoint or connection URL for profiles default storage google drive redirect. |
| `profiles.default.storage.google_drive.token_uri` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__STORAGE__GOOGLE_DRIVE__TOKEN_URI` | Credential or authentication setting for the related subsystem. |
| `profiles.default.scope.roots` | `["${FILE_MCP_ROOT}"]` | `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ROOTS` | Configuration value for profiles default scope roots. |
| `profiles.default.scope.allow_globs` | `["**/*"]` | `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ALLOW_GLOBS` | Configuration value for profiles default scope allow globs. |
| `profiles.default.scope.deny_globs` | `["**/.git/**"]` | `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__DENY_GLOBS` | Configuration value for profiles default scope deny globs. |
| `profiles.default.scope.allowed_exts` | `[]` | `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__ALLOWED_EXTS` | Configuration value for profiles default scope allowed exts. |
| `profiles.default.scope.read_only_exts` | `[]` | `CLOUD_DOG__PROFILES__DEFAULT__SCOPE__READ_ONLY_EXTS` | Configuration value for profiles default scope read only exts. |
| `profiles.default.audit.log_path` | `${FILE_MCP_AUDIT_LOG}` | `CLOUD_DOG__PROFILES__DEFAULT__AUDIT__LOG_PATH` | Configuration value for profiles default audit log path. |
| `profiles.default.audit.include_content_hashes` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__AUDIT__INCLUDE_CONTENT_HASHES` | Configuration value for profiles default audit include content hashes. |
| `profiles.default.snapshots.enabled` | `false` | `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__ENABLED` | Toggle for profiles default snapshots. |
| `profiles.default.snapshots.mode` | `none` | `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__MODE` | Configuration value for profiles default snapshots mode. |
| `profiles.default.snapshots.dir` | `${FILE_MCP_SNAPSHOT_DIR}` | `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__DIR` | Configuration value for profiles default snapshots dir. |
| `profiles.default.snapshots.retention_days` | `30` | `CLOUD_DOG__PROFILES__DEFAULT__SNAPSHOTS__RETENTION_DAYS` | Configuration value for profiles default snapshots retention days. |
| `profiles.default.validation.default_mode` | `warn` | `CLOUD_DOG__PROFILES__DEFAULT__VALIDATION__DEFAULT_MODE` | Configuration value for profiles default validation default mode. |
| `profiles.default.conversion.enabled` | `false` | `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__ENABLED` | Toggle for profiles default conversion. |
| `profiles.default.conversion.backends` | `[]` | `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__BACKENDS` | Configuration value for profiles default conversion backends. |
| `profiles.default.conversion.max_input_mb` | `25` | `CLOUD_DOG__PROFILES__DEFAULT__CONVERSION__MAX_INPUT_MB` | Configuration value for profiles default conversion max input mb. |
| `profiles.default.observability.enabled` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__ENABLED` | Toggle for profiles default observability. |
| `profiles.default.observability.log_path` | `${FILE_MCP_SERVER_LOG}` | `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__LOG_PATH` | Configuration value for profiles default observability log path. |
| `profiles.default.observability.level` | `INFO` | `CLOUD_DOG__PROFILES__DEFAULT__OBSERVABILITY__LEVEL` | Configuration value for profiles default observability level. |
| `profiles.default.limits.search_max_results` | `250` | `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_MAX_RESULTS` | Configuration value for profiles default limits search max results. |
| `profiles.default.limits.search_max_file_mb` | `5` | `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_MAX_FILE_MB` | Configuration value for profiles default limits search max file mb. |
| `profiles.default.limits.search_timeout_s` | `30` | `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__SEARCH_TIMEOUT_S` | Configuration value for profiles default limits search timeout s. |
| `profiles.default.limits.storage_timeout_s` | `30` | `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__STORAGE_TIMEOUT_S` | Configuration value for profiles default limits storage timeout s. |
| `profiles.default.limits.conversion_timeout_s` | `60` | `CLOUD_DOG__PROFILES__DEFAULT__LIMITS__CONVERSION_TIMEOUT_S` | Configuration value for profiles default limits conversion timeout s. |
| `profiles.default.jobs.enabled` | `${FILE_MCP_JOBS_ENABLED:true}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__ENABLED` | Toggle for profiles default jobs. |
| `profiles.default.jobs.backend` | `${FILE_MCP_JOBS_BACKEND:sql}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__BACKEND` | Configuration value for profiles default jobs backend. |
| `profiles.default.jobs.queue_name` | `${FILE_MCP_JOBS_QUEUE:file-mcp}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__QUEUE_NAME` | Configuration value for profiles default jobs queue name. |
| `profiles.default.jobs.payload_max_bytes` | `${FILE_MCP_JOBS_PAYLOAD_MAX_BYTES:65536}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__PAYLOAD_MAX_BYTES` | Configuration value for profiles default jobs payload max bytes. |
| `profiles.default.jobs.sql_url` | `${FILE_MCP_JOBS_SQL_URL:sqlite:///database/file_mcp.db}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__SQL_URL` | Endpoint or connection URL for profiles default jobs sql. |
| `profiles.default.jobs.redis_url` | `${FILE_MCP_JOBS_REDIS_URL:disabled}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__REDIS_URL` | Endpoint or connection URL for profiles default jobs redis. |
| `profiles.default.jobs.redis_key_prefix` | `${FILE_MCP_JOBS_REDIS_KEY_PREFIX:file_mcp_jobs}` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__REDIS_KEY_PREFIX` | Credential or authentication setting for the related subsystem. |
| `profiles.default.jobs.retry.max_attempts` | `3` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__RETRY__MAX_ATTEMPTS` | Maximum retry attempts for failed jobs. |
| `profiles.default.jobs.retry.initial_delay_seconds` | `1.0` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__RETRY__INITIAL_DELAY_SECONDS` | Initial backoff delay between job retries. |
| `profiles.default.jobs.retry.max_delay_seconds` | `30.0` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__RETRY__MAX_DELAY_SECONDS` | Maximum backoff delay between job retries. |
| `profiles.default.jobs.timeout.run_timeout_ms` | `300000` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__TIMEOUT__RUN_TIMEOUT_MS` | Maximum runtime for a single job execution in milliseconds. |
| `profiles.default.jobs.timeout.claim_timeout_ms` | `60000` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__TIMEOUT__CLAIM_TIMEOUT_MS` | Timeout for claiming a job from the queue in milliseconds. |
| `profiles.default.jobs.maintenance.claim_timeout_seconds` | `60` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__MAINTENANCE__CLAIM_TIMEOUT_SECONDS` | Maintenance sweep claim timeout in seconds. |
| `profiles.default.jobs.maintenance.max_age_seconds` | `86400` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__MAINTENANCE__MAX_AGE_SECONDS` | Maximum age before a job is eligible for maintenance cleanup. |
| `profiles.default.jobs.dead_letter.enabled` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__DEAD_LETTER__ENABLED` | Toggle for dead letter queue. |
| `profiles.default.jobs.dead_letter.queue_name` | `dead_letter` | `CLOUD_DOG__PROFILES__DEFAULT__JOBS__DEAD_LETTER__QUEUE_NAME` | Dead letter queue name for failed jobs. |
| `profiles.default.endpoint_health.enabled` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__ENABLED` | Toggle for profiles default endpoint health. |
| `profiles.default.endpoint_health.check_on_startup` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__CHECK_ON_STARTUP` | Configuration value for profiles default endpoint health check on startup. |
| `profiles.default.endpoint_health.check_all_configured_backends` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__CHECK_ALL_CONFIGURED_BACKENDS` | Configuration value for profiles default endpoint health check all configured backends. |
| `profiles.default.endpoint_health.max_retries` | `3` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__MAX_RETRIES` | Configuration value for profiles default endpoint health max retries. |
| `profiles.default.endpoint_health.retry_interval_s` | `2` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RETRY_INTERVAL_S` | Configuration value for profiles default endpoint health retry interval s. |
| `profiles.default.endpoint_health.retry_window_s` | `30` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RETRY_WINDOW_S` | Configuration value for profiles default endpoint health retry window s. |
| `profiles.default.endpoint_health.max_failures_before_restart` | `5` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__MAX_FAILURES_BEFORE_RESTART` | Configuration value for profiles default endpoint health max failures before restart. |
| `profiles.default.endpoint_health.recover_after_s` | `30` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RECOVER_AFTER_S` | Configuration value for profiles default endpoint health recover after s. |
| `profiles.default.endpoint_health.restart_on_threshold` | `false` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RESTART_ON_THRESHOLD` | Configuration value for profiles default endpoint health restart on threshold. |
| `profiles.default.endpoint_health.restart_exit_code` | `75` | `CLOUD_DOG__PROFILES__DEFAULT__ENDPOINT_HEALTH__RESTART_EXIT_CODE` | Configuration value for profiles default endpoint health restart exit code. |

## `web_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `web_server.host` | `${CLOUD_DOG__WEB_SERVER__HOST:0.0.0.0}` | `CLOUD_DOG__WEB_SERVER__HOST` | Host binding or upstream host for web server. |
| `web_server.port` | `${CLOUD_DOG__WEB_SERVER__PORT:8061}` | `CLOUD_DOG__WEB_SERVER__PORT` | Port for web server connections. |
| `web_server.enabled` | `${CLOUD_DOG__WEB_SERVER__ENABLED:true}` | `CLOUD_DOG__WEB_SERVER__ENABLED` | Toggle for web server. |
