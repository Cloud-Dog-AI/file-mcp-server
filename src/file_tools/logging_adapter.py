"""Logging adapter entry points for runtime code.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Stable runtime imports for cloud_dog_logging integration.
Requirements: FR1.3
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-19: Added adapter shim for operational logger configuration.
"""

from __future__ import annotations

from cloud_dog_logging import AppLogger  # type: ignore[import-untyped]

from .config.models import ProfileConfig
from .observability import configure_operational_logger


def configure_logging_for_profile(
    profile: ProfileConfig,
    *,
    name: str = "file_mcp_server",
    service_name: str = "file-mcp-server",
) -> AppLogger:
    return configure_operational_logger(
        profile,
        name=name,
        service_name=service_name,
    )
