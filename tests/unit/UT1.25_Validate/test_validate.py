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


def test_validate_json() -> None:
    assert validate_json('{"a": 1}').valid
    assert not validate_json("{bad}").valid


def test_validate_yaml() -> None:
    assert validate_yaml("a: 1\n").valid
    assert not validate_yaml("a: [\n").valid


def test_validate_xml() -> None:
    assert validate_xml("<root />").valid
    assert not validate_xml("<root>").valid


def test_validate_html() -> None:
    result = validate_html("<html><body></body></html>")
    assert isinstance(result, ValidationResult)
    assert result.valid


def test_validate_markdown() -> None:
    assert validate_markdown("# Title\n## Subtitle").valid
    assert not validate_markdown("# Title\n### Skipped").valid


def test_validation_strict_mode(tmp_path: Path) -> None:
    validation = _validation_config(tmp_path, default_mode="strict")
    result = validate_with_mode("json", "{bad}", validation)
    assert not result.valid
    assert result.errors


def test_validation_warn_mode(tmp_path: Path) -> None:
    validation = _validation_config(
        tmp_path, default_mode="strict", per_type={"markdown": "warn"}
    )
    result = validate_with_mode("markdown", "# Title\n### Skipped", validation)
    assert result.valid
    assert result.warnings


def test_validation_ignore_mode(tmp_path: Path) -> None:
    validation = _validation_config(tmp_path, default_mode="ignore")
    result = validate_with_mode("json", "{bad}", validation)
    assert result.valid
    assert not result.errors
