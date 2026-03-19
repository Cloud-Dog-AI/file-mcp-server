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

"""YAML codec adapter for external yaml library usage.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Shared adapter for safe YAML load/dump operations.
Requirements: FR1.3
Tasks: W25A-B
Architecture: 4.3 External service interface pattern
Tests: QT1.1, QT1.2
"""

from __future__ import annotations

from typing import Any

import yaml

YAMLError = yaml.YAMLError


def safe_load(text: str) -> Any:
    """Parse YAML text with safe loader semantics."""
    return yaml.safe_load(text)


def safe_dump(value: Any, *, sort_keys: bool = False) -> str:
    """Serialise Python data to YAML text with safe dumper semantics."""
    return yaml.safe_dump(value, sort_keys=sort_keys)
