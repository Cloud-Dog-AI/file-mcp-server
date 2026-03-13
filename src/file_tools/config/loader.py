# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# """
# License: Apache 2.0
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

"""Compatibility shim for legacy config loader imports.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Backward-compatible wrapper re-exporting adapter entry points.
Requirements: NF1.7
Tasks: T18
Architecture: 3.3 Example schema
Tests: UT1.1
Recent Change History:
- 2026-02-19: Replaced bespoke loader with cloud_dog_config adapter shim.
"""

from __future__ import annotations

from .adapter import get_profile, load_config

__all__ = ["get_profile", "load_config"]
