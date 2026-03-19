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

"""Logging adapter entry points for runtime code.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Stable runtime imports for cloud_dog_logging integration.
Requirements: FR1.3
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-19: Added adapter shim for operational logger configuration.
"""

from __future__ import annotations

from cloud_dog_logging import AppLogger  # type: ignore[import-untyped]

from .config.models import ProfileConfig
from .observability import configure_operational_logger


def configure_logging_for_profile(
    profile: ProfileConfig,
    *,
    name: str = "file_mcp_server",
    service_name: str = "file-mcp-server",
) -> AppLogger:
    """Execute configure logging for profile."""
    return configure_operational_logger(
        profile,
        name=name,
        service_name=service_name,
    )
