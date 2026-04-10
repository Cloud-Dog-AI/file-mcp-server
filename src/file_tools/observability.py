# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Operational logging bridge to cloud_dog_logging.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Configure PS-40 logging from loaded Server/Profile config models.
Requirements: NF1.3, FR1.3
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-19: Replaced bespoke logger bootstrap with cloud_dog_logging setup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cloud_dog_logging import (  # type: ignore[import-untyped]
    AppLogger,
    get_logger,
    setup_logging,
)

from .config.models import ObservabilityConfig, ProfileConfig


def _clean_path(value: str | None) -> str | None:
    """Handle clean path."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or "${" in cleaned:
        return None
    return cleaned


def _apply_log_permissions(path_value: str | None, mode: int) -> None:
    """Normalize created log file permissions for compliance checks."""
    if not path_value:
        return
    try:
        log_path = Path(path_value)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch(exist_ok=True)
        log_path.chmod(mode)
    except OSError:
        return


def _coerce_profile(
    config: ObservabilityConfig | ProfileConfig,
) -> tuple[ObservabilityConfig, str | None, str | None]:
    """Handle coerce profile."""
    if isinstance(config, ProfileConfig):
        return (
            config.observability,
            _clean_path(config.audit.log_path),
            _clean_path(config.server_id),
        )
    return config, None, None


def configure_operational_logger(
    config: ObservabilityConfig | ProfileConfig,
    *,
    name: str = "file_mcp_server",
    service_name: str = "file-mcp-server",
    server_id: str | None = None,
    app_log_path: str | None = None,
    environment: str | None = None,
) -> AppLogger:
    """Configure cloud_dog_logging from already-loaded profile settings."""
    observability, audit_path, profile_server_id = _coerce_profile(config)
    app_path = _clean_path(app_log_path) or _clean_path(observability.log_path)
    enabled = observability.enabled is not False
    level = (observability.level or "INFO").strip().upper() or "INFO"
    resolved_server_id = (
        _clean_path(server_id) or profile_server_id or f"{service_name}-local"
    )
    resolved_environment = (
        _clean_path(environment)
        or _clean_path(os.getenv("CLOUD_DOG_ENVIRONMENT"))
        or "dev"
    )

    payload: dict[str, Any] = {
        "service_name": service_name,
        "environment": resolved_environment,
        "service_instance": resolved_server_id,
        "log": {
            "level": level,
            "format": "json",
            "environment": resolved_environment,
            "service_instance": resolved_server_id,
            "app_log": app_path if enabled else None,
            "audit_log": audit_path,
            "console": bool(enabled and not app_path),
            "redaction": {"presets": ["default", "file_tools"]},
        },
    }
    setup_logging(payload)
    if enabled:
        _apply_log_permissions(app_path, 0o644)
    return get_logger(name)
