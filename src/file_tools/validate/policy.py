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

"""Validation policy helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Apply validation modes to validator results based on configuration.
Requirements: FR1.18
Tasks: T11
Architecture: 6.6 Validation
Tests: UT1.13
Recent Change History:
- 2026-02-05: Add validation policy helpers for strict/warn/ignore modes.
"""

from __future__ import annotations

from typing import Callable, Dict

from file_tools.config.models import ValidationConfig

from .validators import (
    ValidationResult,
    validate_html,
    validate_json,
    validate_markdown,
    validate_xml,
    validate_yaml,
)

_VALIDATORS: Dict[str, Callable[[str], ValidationResult]] = {
    "json": validate_json,
    "yaml": validate_yaml,
    "xml": validate_xml,
    "html": validate_html,
    "markdown": validate_markdown,
}


def select_validation_mode(validation: ValidationConfig, content_type: str) -> str:
    """Execute select validation mode."""
    if validation.per_type and content_type in validation.per_type:
        return validation.per_type[content_type]
    return validation.default_mode or "strict"


def apply_validation_mode(result: ValidationResult, mode: str) -> ValidationResult:
    """Execute apply validation mode."""
    normalized = mode.lower()
    if normalized == "strict":
        return result
    if normalized == "ignore":
        return ValidationResult(valid=True)
    if normalized == "warn":
        if result.valid:
            return result
        return ValidationResult(valid=True, warnings=result.errors)
    raise ValueError(f"Unknown validation mode: {mode}")


def validate_with_mode(
    content_type: str, text: str, validation: ValidationConfig
) -> ValidationResult:
    """Validate with mode."""
    if content_type not in _VALIDATORS:
        raise ValueError(f"Unsupported validation type: {content_type}")
    mode = select_validation_mode(validation, content_type)
    result = _VALIDATORS[content_type](text)
    return apply_validation_mode(result, mode)
