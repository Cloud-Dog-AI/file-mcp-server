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

from typing import Any

from cloud_dog_logging import (  # type: ignore[import-untyped]
    AppLogger,
    get_logger,
    setup_logging,
)

from .config.models import ObservabilityConfig, ProfileConfig


def _clean_path(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or "${" in cleaned:
        return None
    return cleaned


def _coerce_profile(
    config: ObservabilityConfig | ProfileConfig,
) -> tuple[ObservabilityConfig, str | None]:
    if isinstance(config, ProfileConfig):
        return config.observability, _clean_path(config.audit.log_path)
    return config, None


def configure_operational_logger(
    config: ObservabilityConfig | ProfileConfig,
    *,
    name: str = "file_mcp_server",
    service_name: str = "file-mcp-server",
) -> AppLogger:
    """Configure cloud_dog_logging from already-loaded profile settings."""
    observability, audit_path = _coerce_profile(config)
    app_path = _clean_path(observability.log_path)
    enabled = observability.enabled is not False
    level = (observability.level or "INFO").strip().upper() or "INFO"

    payload: dict[str, Any] = {
        "service_name": service_name,
        "log": {
            "level": level,
            "format": "json",
            "app_log": app_path if enabled else None,
            "audit_log": audit_path,
            "console": bool(enabled and not app_path),
            "redaction": {"presets": ["default", "file_tools"]},
        },
    }
    setup_logging(payload)
    return get_logger(name)
