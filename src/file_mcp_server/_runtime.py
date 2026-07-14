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

"""
file-mcp-server — file_mcp_server/_runtime.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Project-local Python runtime contract (W28R-3013 supply-chain
    remediation). file-mcp-server is remediated to CPython 3.13 to clear the
    fixable CPython High/Critical CVEs carried by the 3.12 base image
    (CVE-2026-3298/3644/4224/4786/6100/7210/9669). This module fails closed if
    the interpreter is older than the required minimum, so the contract is
    enforced for the container, the local .venv, and the test harness alike —
    not only in the Dockerfile.
Requirements: NF-006 (Python 3.13 runtime contract).
Tests: tests/unit/UT1.60_RuntimeContract/test_ut_runtime_contract.py.
"""

from __future__ import annotations

import sys

# Minimum supported interpreter for file-mcp-server (major, minor).
MIN_PYTHON: tuple[int, int] = (3, 13)


def is_supported_runtime(
    version_info: tuple[int, ...] | None = None,
    minimum: tuple[int, int] = MIN_PYTHON,
) -> bool:
    """Return True when the running (or supplied) interpreter meets the minimum.

    Args:
        version_info: Optional (major, minor, ...) tuple to test. Defaults to the
            live ``sys.version_info``.
        minimum: Required (major, minor) floor. Defaults to :data:`MIN_PYTHON`.

    Returns:
        bool: True if ``version_info[:2] >= minimum``.
    """
    current = (
        tuple(version_info[:2]) if version_info is not None else sys.version_info[:2]
    )
    return current >= tuple(minimum)


def enforce_runtime(
    version_info: tuple[int, ...] | None = None,
    minimum: tuple[int, int] = MIN_PYTHON,
) -> None:
    """Fail closed unless the interpreter satisfies the runtime contract.

    Raises:
        RuntimeError: if the interpreter is older than ``minimum``.
    """
    if not is_supported_runtime(version_info, minimum):
        current = (
            tuple(version_info[:2])
            if version_info is not None
            else sys.version_info[:2]
        )
        want = ".".join(str(p) for p in minimum)
        have = ".".join(str(p) for p in current)
        raise RuntimeError(
            f"file-mcp-server requires Python >= {want} (NF-006 runtime contract); "
            f"found {have}. Create a Python {want} virtual environment "
            f"(python{want} -m venv .venv) and reinstall."
        )
