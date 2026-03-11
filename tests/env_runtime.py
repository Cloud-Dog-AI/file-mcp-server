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
