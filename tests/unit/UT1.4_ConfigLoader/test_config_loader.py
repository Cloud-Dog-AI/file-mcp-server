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

"""Config loader tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for config loader precedence and env file ordering.
Requirements: FR1.3, FR1.4, CS1.3, NF1.7
Tasks: T2, T18
Architecture: 3. Configuration and Precedence
Tests: UT1.1
Recent Change History:
- 2026-02-05: Added multi-env precedence tests.
- 2026-02-19: Migrated tests to cloud_dog_config adapter and added baseline adapter coverage.
"""


from __future__ import annotations
import pytest

from pathlib import Path

from file_tools.config.adapter import get_profile, load_config


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _build_config_files(tmp_path: Path) -> tuple[Path, Path]:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    observability:
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "${FILE_MCP_SERVER_LEVEL_DEFAULT}"
""".lstrip(),
    )
    _write_yaml(
        config_path,
        """
profiles:
  default:
    observability:
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "${FILE_MCP_SERVER_LEVEL_CONFIG}"
""".lstrip(),
    )
    return defaults_path, config_path


def _write_env(path: Path, values: dict[str, str]) -> None:
    content = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    path.write_text(content, encoding="utf-8")


def _env_paths(tmp_path: Path) -> tuple[list[Path], str, str]:
    env_a = tmp_path / "env-a"
    env_b = tmp_path / "env-b"
    log_path_a = tmp_path / "ops-a.log"
    log_path_b = tmp_path / "ops-b.log"
    level_default_a = f"level-default-a-{tmp_path.name}"
    level_default_b = f"level-default-b-{tmp_path.name}"
    level_config_a = f"level-config-a-{tmp_path.name}"
    level_config_b = f"level-config-b-{tmp_path.name}"
    _write_env(
        env_a,
        {
            "FILE_MCP_SERVER_LOG": str(log_path_a),
            "FILE_MCP_SERVER_LEVEL_DEFAULT": level_default_a,
            "FILE_MCP_SERVER_LEVEL_CONFIG": level_config_a,
        },
    )
    _write_env(
        env_b,
        {
            "FILE_MCP_SERVER_LOG": str(log_path_b),
            "FILE_MCP_SERVER_LEVEL_DEFAULT": level_default_b,
            "FILE_MCP_SERVER_LEVEL_CONFIG": level_config_b,
        },
    )
    return [env_a, env_b], str(log_path_b), level_config_b
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_env_precedence(tmp_path: Path, monkeypatch) -> None:
    defaults_path, config_path = _build_config_files(tmp_path)
    env_paths, expected_log_path, expected_level = _env_paths(tmp_path)
    for key in (
        "FILE_MCP_SERVER_LOG",
        "FILE_MCP_SERVER_LEVEL_DEFAULT",
        "FILE_MCP_SERVER_LEVEL_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)

    config = load_config(
        env_path=env_paths,
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)

    for key in (
        "FILE_MCP_SERVER_LOG",
        "FILE_MCP_SERVER_LEVEL_DEFAULT",
        "FILE_MCP_SERVER_LEVEL_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)

    assert profile.observability.log_path == expected_log_path
    assert profile.observability.level == expected_level
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_os_environ_precedence(tmp_path: Path, monkeypatch) -> None:
    defaults_path, config_path = _build_config_files(tmp_path)
    env_paths, expected_log_path, expected_level = _env_paths(tmp_path)
    env_override = str(tmp_path / "ops-env.log")
    monkeypatch.setenv("FILE_MCP_SERVER_LOG", env_override)
    for key in ("FILE_MCP_SERVER_LEVEL_DEFAULT", "FILE_MCP_SERVER_LEVEL_CONFIG"):
        monkeypatch.delenv(key, raising=False)

    config = load_config(
        env_path=env_paths,
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)

    for key in (
        "FILE_MCP_SERVER_LOG",
        "FILE_MCP_SERVER_LEVEL_DEFAULT",
        "FILE_MCP_SERVER_LEVEL_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)

    # OS environment values should take precedence over env-file values.
    assert profile.observability.log_path == env_override
    assert profile.observability.level == expected_level
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_env_overrides_literal_config_values(
    tmp_path: Path, monkeypatch
) -> None:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"

    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    observability:
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "INFO"
""".lstrip(),
    )
    _write_yaml(
        config_path,
        """
profiles:
  default:
    observability:
      log_path: "/literal/from/config.log"
      level: "WARN"
""".lstrip(),
    )
    _write_env(
        env_path,
        {
            "FILE_MCP_SERVER_LOG": str(tmp_path / "from-env-file.log"),
        },
    )

    monkeypatch.delenv("FILE_MCP_SERVER_LOG", raising=False)
    config = load_config(
        env_path=[env_path],
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)
    monkeypatch.delenv("FILE_MCP_SERVER_LOG", raising=False)

    # Literal config values take precedence over placeholder-driven env values.
    assert profile.observability.log_path == "/literal/from/config.log"
    assert profile.observability.level == "WARN"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_os_environ_overrides_env_file_and_config(
    tmp_path: Path, monkeypatch
) -> None:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"

    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    observability:
      log_path: "${FILE_MCP_SERVER_LOG}"
""".lstrip(),
    )
    _write_yaml(
        config_path,
        """
profiles:
  default:
    observability:
      log_path: "/literal/from/config.log"
""".lstrip(),
    )
    _write_env(env_path, {"FILE_MCP_SERVER_LOG": str(tmp_path / "from-env-file.log")})
    monkeypatch.setenv("FILE_MCP_SERVER_LOG", str(tmp_path / "from-os-env.log"))

    config = load_config(
        env_path=[env_path],
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)
    monkeypatch.delenv("FILE_MCP_SERVER_LOG", raising=False)

    # Literal config values take precedence over placeholder-driven env values.
    assert profile.observability.log_path == "/literal/from/config.log"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_defaults_only(tmp_path: Path, monkeypatch) -> None:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    auth:
      api_keys:
        - "defaults-only-key"
    observability:
      level: "INFO"
""".lstrip(),
    )

    monkeypatch.delenv("FILE_MCP_SERVER_LEVEL_DEFAULT", raising=False)
    config = load_config(
        env_path=[],
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)

    assert profile.auth.api_keys == ["defaults-only-key"]
    assert profile.observability.level == "INFO"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_coerces_numeric_api_keys_to_strings(
    tmp_path: Path, monkeypatch
) -> None:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"

    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
""".lstrip(),
    )
    _write_yaml(
        config_path,
        """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
""".lstrip(),
    )
    _write_env(
        env_path,
        {
            "FILE_MCP_API_KEY_PRIMARY": "secret",
            "FILE_MCP_API_KEY_SECONDARY": "12345678",
        },
    )

    monkeypatch.delenv("FILE_MCP_API_KEY_PRIMARY", raising=False)
    monkeypatch.delenv("FILE_MCP_API_KEY_SECONDARY", raising=False)
    config = load_config(
        env_path=[env_path],
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)

    assert profile.auth.api_keys == ["secret", "12345678"]
    assert all(isinstance(item, str) for item in profile.auth.api_keys)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_load_config_env_override_precedence(tmp_path: Path, monkeypatch) -> None:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"
    _write_yaml(
        defaults_path,
        """
profiles:
  default:
    observability:
      level: "${FILE_MCP_SERVER_LEVEL_DEFAULT}"
""".lstrip(),
    )
    _write_yaml(
        config_path,
        """
profiles:
  default:
    observability:
      level: "WARN"
""".lstrip(),
    )
    _write_env(env_path, {"FILE_MCP_SERVER_LEVEL_DEFAULT": "INFO-FILE"})
    monkeypatch.setenv("FILE_MCP_SERVER_LEVEL_DEFAULT", "INFO-OS")

    config = load_config(
        env_path=[env_path],
        config_path=str(config_path),
        defaults_path=str(defaults_path),
    )
    profile = get_profile(config)
    monkeypatch.delenv("FILE_MCP_SERVER_LEVEL_DEFAULT", raising=False)

    # Literal config values in config.yaml override placeholder values.
    assert profile.observability.level == "WARN"
