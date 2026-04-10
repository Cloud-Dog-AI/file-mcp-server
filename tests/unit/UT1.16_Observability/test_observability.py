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

import json
from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.config.adapter import load_config
from file_tools.observability import configure_operational_logger
from file_tools.logging_adapter import configure_logging_for_profile


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
        "CLOUD_DOG_ENVIRONMENT": "test",
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


def test_operational_logger_writes_file(
    tmp_path: Path, monkeypatch
) -> None:
    profile, log_path = _build_profile(tmp_path, enabled=True, name="ops")
    monkeypatch.setenv("CLOUD_DOG_ENVIRONMENT", "test")

    logger = configure_operational_logger(
        profile.observability, name="test_observability_write"
    )
    logger.info("hello")

    content = log_path.read_text(encoding="utf-8")
    assert "hello" in content
    entry = json.loads(content.strip().splitlines()[-1])
    assert entry["environment"] == "test"
    assert (log_path.stat().st_mode & 0o777) == 0o644


def test_operational_logger_disabled(tmp_path: Path) -> None:
    profile, log_path = _build_profile(tmp_path, enabled=False, name="ops-disabled")

    logger = configure_operational_logger(
        profile.observability, name="test_observability_disabled"
    )
    logger.info("skip")

    assert not log_path.exists()


def test_configure_logging_for_profile_uses_role_specific_log_file(tmp_path: Path) -> None:
    api_log = tmp_path / "logs" / "api_server.log"
    fallback_log = tmp_path / "fallback.log"
    defaults_yaml = """
profiles:
  default:
    server_id: "file-mcp-ut"
    audit:
      log_path: "${FILE_MCP_AUDIT_LOG}"
    observability:
      enabled: "true"
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "INFO"
log:
  environment: "${CLOUD_DOG_ENVIRONMENT}"
  api_server_log: "${FILE_MCP_API_SERVER_LOG}"
""".lstrip()
    env_values = {
        "CLOUD_DOG_ENVIRONMENT": "st",
        "FILE_MCP_AUDIT_LOG": str(tmp_path / "audit.log.jsonl"),
        "FILE_MCP_SERVER_LOG": str(fallback_log),
        "FILE_MCP_API_SERVER_LOG": str(api_log),
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )
    config = load_config(
        env_path=str(tmp_path / "env"),
        config_path=str(tmp_path / "config.yaml"),
        defaults_path=str(tmp_path / "defaults.yaml"),
        root_dir=str(tmp_path),
    )

    logger = configure_logging_for_profile(
        profile,
        config=config,
        role="api",
        name="test_role_specific_observability",
    )
    logger.info("role-specific-log")

    assert api_log.exists()
    entry = json.loads(api_log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert entry["message"] == "role-specific-log"
    assert entry["environment"] == "st"
    assert (api_log.stat().st_mode & 0o777) == 0o644
    assert not fallback_log.exists()
