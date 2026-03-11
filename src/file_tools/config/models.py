"""file_tools configuration models.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Pydantic configuration models for file-mcp-server profiles.
Requirements: NF1.2, NF1.3, CS1.5
Tasks: T18
Architecture: 3.3 Example schema, 7.2 Performance, 7.4 Observability
Tests: ST1.6, ST1.7
Recent Change History:
- 2026-02-05: Added observability and limits config models.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    api_keys: List[str] = Field(default_factory=list)
    header_name: Optional[str] = None
    header_scheme: Optional[str] = None


class HttpServerConfig(BaseModel):
    transport: Optional[str] = None
    host: Optional[str] = None
    fallback_host: Optional[str] = None
    port: Optional[int | str] = None
    base_path: Optional[str] = None
    mcp_path: Optional[str] = None
    health_path: Optional[str] = None
    events_path: Optional[str] = None
    stateless_http: Optional[bool | str] = None


class ScopeConfig(BaseModel):
    roots: List[str] = Field(default_factory=list)
    allow_globs: List[str] = Field(default_factory=list)
    deny_globs: List[str] = Field(default_factory=list)
    allowed_exts: List[str] = Field(default_factory=list)
    read_only_exts: List[str] = Field(default_factory=list)


class AuditConfig(BaseModel):
    log_path: Optional[str] = None
    include_content_hashes: Optional[bool] = None


class SnapshotConfig(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    dir: Optional[str] = None
    retention_days: Optional[int] = None
    retention_count: Optional[int] = None
    max_storage_mb: Optional[int] = None


class ValidationConfig(BaseModel):
    default_mode: Optional[str] = None
    per_type: Dict[str, str] = Field(default_factory=dict)


class ConversionConfig(BaseModel):
    enabled: Optional[bool] = None
    backends: List[str] = Field(default_factory=list)
    max_input_mb: Optional[int] = None


class ObservabilityConfig(BaseModel):
    enabled: Optional[bool] = None
    log_path: Optional[str] = None
    level: Optional[str] = None


class LimitsConfig(BaseModel):
    search_max_results: Optional[int] = None
    search_max_file_mb: Optional[int] = None
    search_timeout_s: Optional[int] = None
    storage_timeout_s: Optional[int] = None
    conversion_timeout_s: Optional[int] = None


class TlsConfig(BaseModel):
    """
    TLS controls for outbound connections to remote storage backends.

    - insecure_skip_verify: when true, disable certificate verification.
    - ca_bundle_path: optional CA bundle file path to trust.
    """

    insecure_skip_verify: Optional[bool | str] = None
    ca_bundle_path: Optional[str] = None


class S3StorageConfig(BaseModel):
    endpoint: Optional[str] = None
    bucket: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    prefix: Optional[str] = None


class WebDavStorageConfig(BaseModel):
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    move_retry_count: Optional[int | str] = None
    move_retry_backoff_s: Optional[float | str] = None
    move_probe_timeout_s: Optional[float | str] = None
    move_retry_statuses: Optional[str] = None


class FtpStorageConfig(BaseModel):
    host: Optional[str] = None
    port: Optional[int | str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    base_dir: Optional[str] = None
    use_tls: Optional[bool | str] = None


class GoogleDriveStorageConfig(BaseModel):
    user_email: Optional[str] = None
    folder_id: Optional[str] = None
    folder_url: Optional[str] = None
    folder_url_example: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    oauth_scope: Optional[str] = None
    oauth_authorize_uri: Optional[str] = None
    api_base_uri: Optional[str] = None
    upload_base_uri: Optional[str] = None
    redirect_uri: Optional[str] = None
    token_uri: Optional[str] = None


class StorageConfig(BaseModel):
    """
    Storage backend configuration.

    backend:
      - local: native filesystem paths (current behaviour)
      - s3: S3-compatible object storage (keyspace)
      - webdav: WebDAV over HTTP(S)
      - ftp: FTP/FTPS
    """

    backend: Optional[str] = None
    tls: TlsConfig = Field(default_factory=TlsConfig)
    s3: S3StorageConfig = Field(default_factory=S3StorageConfig)
    webdav: WebDavStorageConfig = Field(default_factory=WebDavStorageConfig)
    ftp: FtpStorageConfig = Field(default_factory=FtpStorageConfig)
    google_drive: GoogleDriveStorageConfig = Field(
        default_factory=GoogleDriveStorageConfig
    )


class EndpointHealthConfig(BaseModel):
    enabled: Optional[bool | str] = None
    check_on_startup: Optional[bool | str] = None
    check_all_configured_backends: Optional[bool | str] = None
    max_retries: Optional[int | str] = None
    retry_interval_s: Optional[int | str] = None
    retry_window_s: Optional[int | str] = None
    max_failures_before_restart: Optional[int | str] = None
    recover_after_s: Optional[int | str] = None
    restart_on_threshold: Optional[bool | str] = None
    restart_exit_code: Optional[int | str] = None


class ProfileConfig(BaseModel):
    auth: AuthConfig = Field(default_factory=AuthConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    scope: ScopeConfig = Field(default_factory=ScopeConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    snapshots: SnapshotConfig = Field(default_factory=SnapshotConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    endpoint_health: EndpointHealthConfig = Field(default_factory=EndpointHealthConfig)


class ServerConfig(BaseModel):
    profiles: Dict[str, ProfileConfig] = Field(default_factory=dict)
    http: HttpServerConfig = Field(default_factory=HttpServerConfig)
