"""Validation package (scaffold)."""

from .validators import (
    ValidationResult,
    validate_html,
    validate_json,
    validate_markdown,
    validate_xml,
    validate_yaml,
)

__all__ = [
    "ValidationResult",
    "validate_html",
    "validate_json",
    "validate_markdown",
    "validate_xml",
    "validate_yaml",
]
