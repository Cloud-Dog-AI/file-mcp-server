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

"""Validation policy tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for validation policies and validators.
Requirements: FR1.18
Tasks: T11
Architecture: 6.6 Validation
Tests: UT1.13
Recent Change History:
- 2026-02-05: Align validation tests to config-driven strict/warn/ignore modes.
"""


from __future__ import annotations
import pytest

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.config.models import ValidationConfig
from file_tools.validate import (
    ValidationResult,
    validate_html,
    validate_json,
    validate_markdown,
    validate_xml,
    validate_yaml,
)
from file_tools.validate.policy import validate_with_mode


def _validation_config(
    tmp_path: Path,
    *,
    default_mode: str,
    per_type: dict[str, str] | None = None,
) -> ValidationConfig:
    env_values = {"FILE_MCP_VALIDATION_DEFAULT": default_mode}
    per_type_lines = ""
    if per_type:
        for key, mode in per_type.items():
            env_key = f"FILE_MCP_VALIDATION_{key.upper()}"
            env_values[env_key] = mode
            per_type_lines += f'        {key}: "${{{env_key}}}"\n'

    per_type_block = (
        "      per_type:\n" + per_type_lines
        if per_type_lines
        else "      per_type: {}\n"
    )
    defaults_yaml = (
        "profiles:\n"
        "  default:\n"
        "    validation:\n"
        '      default_mode: "${FILE_MCP_VALIDATION_DEFAULT}"\n'
        f"{per_type_block}"
    )
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )
    return profile.validation
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validate_json() -> None:
    assert validate_json('{"a": 1}').valid
    assert not validate_json("{bad}").valid
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validate_yaml() -> None:
    assert validate_yaml("a: 1\n").valid
    assert not validate_yaml("a: [\n").valid
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validate_xml() -> None:
    assert validate_xml("<root />").valid
    assert not validate_xml("<root>").valid
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validate_html() -> None:
    result = validate_html("<html><body></body></html>")
    assert isinstance(result, ValidationResult)
    assert result.valid
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validate_markdown() -> None:
    assert validate_markdown("# Title\n## Subtitle").valid
    assert not validate_markdown("# Title\n### Skipped").valid
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validation_strict_mode(tmp_path: Path) -> None:
    validation = _validation_config(tmp_path, default_mode="strict")
    result = validate_with_mode("json", "{bad}", validation)
    assert not result.valid
    assert result.errors
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validation_warn_mode(tmp_path: Path) -> None:
    validation = _validation_config(
        tmp_path, default_mode="strict", per_type={"markdown": "warn"}
    )
    result = validate_with_mode("markdown", "# Title\n### Skipped", validation)
    assert result.valid
    assert result.warnings
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-006")


def test_validation_ignore_mode(tmp_path: Path) -> None:
    validation = _validation_config(tmp_path, default_mode="ignore")
    result = validate_with_mode("json", "{bad}", validation)
    assert result.valid
    assert not result.errors
