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
    port: Optional[str] = None
    base_path: Optional[str] = None
    mcp_path: Optional[str] = None
    health_path: Optional[str] = None
    events_path: Optional[str] = None
    stateless_http: Optional[str] = None


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
    conversion_timeout_s: Optional[int] = None


class ProfileConfig(BaseModel):
    auth: AuthConfig = Field(default_factory=AuthConfig)
    scope: ScopeConfig = Field(default_factory=ScopeConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    snapshots: SnapshotConfig = Field(default_factory=SnapshotConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)


class ServerConfig(BaseModel):
    profiles: Dict[str, ProfileConfig] = Field(default_factory=dict)
    http: HttpServerConfig = Field(default_factory=HttpServerConfig)
