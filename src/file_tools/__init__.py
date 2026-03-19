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

from .limits import (
    LimitError,
    enforce_max_file_size,
    enforce_timeout,
    exceeds_max_file_size,
)
from .logging_adapter import configure_logging_for_profile
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
    "configure_logging_for_profile",
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
