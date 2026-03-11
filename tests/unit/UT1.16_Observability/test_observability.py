"""Observability helper tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for operational logger configuration.
Requirements: NF1.3
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-05: Added operational logger tests.
"""

from __future__ import annotations

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.observability import configure_operational_logger


def _build_profile(tmp_path: Path, *, enabled: bool, name: str):
    log_path = tmp_path / f"{name}.log"
    defaults_yaml = """
profiles:
  default:
    observability:
      enabled: "${FILE_MCP_OBSERVABILITY_ENABLED}"
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "${FILE_MCP_SERVER_LEVEL}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_OBSERVABILITY_ENABLED": str(enabled).lower(),
        "FILE_MCP_SERVER_LOG": str(log_path),
        "FILE_MCP_SERVER_LEVEL": "INFO",
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return profile, log_path


def test_operational_logger_writes_file(tmp_path: Path) -> None:
    profile, log_path = _build_profile(tmp_path, enabled=True, name="ops")

    logger = configure_operational_logger(
        profile.observability, name="test_observability_write"
    )
    logger.info("hello")

    content = log_path.read_text(encoding="utf-8")
    assert "hello" in content


def test_operational_logger_disabled(tmp_path: Path) -> None:
    profile, log_path = _build_profile(tmp_path, enabled=False, name="ops-disabled")

    logger = configure_operational_logger(
        profile.observability, name="test_observability_disabled"
    )
    logger.info("skip")

    assert not log_path.exists()
