"""Reusable file tooling package.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Public exports for file tool helpers and utilities.
Requirements: NF1.2, NF1.3, CS1.5
Tasks: T18
Architecture: 7.2 Performance, 7.4 Observability
Tests: ST1.6, ST1.7
Recent Change History:
- 2026-02-05: Added observability and limits exports.
"""

from .limits import LimitError, enforce_max_file_size, enforce_timeout, exceeds_max_file_size
from .observability import configure_operational_logger
from .posix import (
    filter_posix_paths,
    is_posix_path,
    normalize_path,
    require_relative,
    safe_join,
    to_posix,
)

__all__ = [
    "LimitError",
    "configure_operational_logger",
    "enforce_max_file_size",
    "enforce_timeout",
    "exceeds_max_file_size",
    "filter_posix_paths",
    "is_posix_path",
    "normalize_path",
    "require_relative",
    "safe_join",
    "to_posix",
]
