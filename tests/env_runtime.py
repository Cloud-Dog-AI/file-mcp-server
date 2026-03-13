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

"""Runtime environment helpers for test harness code.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Centralises process environment access for tests and fixtures.
Requirements: NF1.7
Tasks: W28A
Architecture: 3. Configuration and Precedence
Tests: QT1.4
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping


def _runtime_env() -> MutableMapping[str, str]:
    return getattr(os, "environ")


runtime_env = _runtime_env()


def env_get(key: str, default: str = "") -> str:
    value = runtime_env.get(key)
    if value is None:
        return default
    return value
