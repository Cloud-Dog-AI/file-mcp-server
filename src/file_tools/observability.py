"""Operational observability helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Configure operational logging separate from audit logging.
Requirements: NF1.3
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-05: Initial operational logger setup helper.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config.models import ObservabilityConfig


def _resolve_level(level: Optional[str]) -> int:
    if not level:
        return logging.INFO
    value = logging.getLevelName(level.upper())
    if isinstance(value, int):
        return value
    return logging.INFO


def configure_operational_logger(
    config: ObservabilityConfig,
    *,
    name: str = "file_mcp_server",
) -> logging.Logger:
    logger = logging.getLogger(name)
    if getattr(logger, "_file_mcp_configured", False):
        return logger

    logger.handlers.clear()
    logger.setLevel(_resolve_level(config.level))
    logger.propagate = False

    if config.enabled is False:
        handler: logging.Handler = logging.NullHandler()
    else:
        if config.log_path:
            log_path = Path(config.log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path, encoding="utf-8")
        else:
            handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    setattr(logger, "_file_mcp_configured", True)
    return logger
