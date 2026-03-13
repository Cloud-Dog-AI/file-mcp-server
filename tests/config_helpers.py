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

"""Test configuration helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Helpers for building profile config from env/config/defaults in tests.
Requirements: NF1.7
Tasks: T18
Architecture: 3. Configuration and Precedence
Tests: UT1.1
Recent Change History:
- 2026-02-05: Added test config helpers for env/config precedence.
- 2026-02-19: Updated helpers to load config through cloud_dog_config adapter.
"""

from __future__ import annotations

from tests.env_runtime import runtime_env

from pathlib import Path
from typing import Mapping


from file_tools.config.adapter import get_profile, load_config
from file_tools.config.models import ProfileConfig


def write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_env(path: Path, values: Mapping[str, str]) -> None:
    content = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    path.write_text(content, encoding="utf-8")


def build_profile(
    tmp_path: Path,
    *,
    env_values: Mapping[str, str],
    defaults_yaml: str,
    config_yaml: str,
) -> ProfileConfig:
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"

    write_env(env_path, env_values)
    write_yaml(defaults_path, defaults_yaml)
    write_yaml(config_path, config_yaml)

    previous_env: dict[str, str | None] = {}
    for key in env_values:
        previous_env[key] = runtime_env.get(key)
        runtime_env.pop(key, None)

    config = load_config(
        env_path=str(env_path),
        config_path=str(config_path),
        defaults_path=str(defaults_path),
        root_dir=str(tmp_path),
    )

    for key, value in previous_env.items():
        if value is None:
            runtime_env.pop(key, None)
        else:
            runtime_env[key] = value
    return get_profile(config)
