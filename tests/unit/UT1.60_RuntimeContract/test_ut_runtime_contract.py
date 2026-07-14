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
file-mcp-server — tests/unit/UT1.60_RuntimeContract/test_ut_runtime_contract.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Enforces the W28R-3013 project-local Python 3.13 runtime contract
    (NF-006). Proves the preflight (a) passes on the live interpreter, which the
    suite therefore proves is >= 3.13, (b) fails closed on Python < 3.13, and (c)
    the version files (.python-version, pyproject requires-python) agree.
Requirements: NF-006.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from file_mcp_server._runtime import MIN_PYTHON, enforce_runtime, is_supported_runtime

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("NF-006")
def test_min_python_is_313() -> None:
    assert MIN_PYTHON == (3, 13)


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("NF-006")
def test_live_interpreter_meets_contract() -> None:
    # The suite must be running on the contracted runtime.
    assert sys.version_info[:2] >= (3, 13), (
        f"tests must run on Python >= 3.13, got {sys.version_info[:3]}"
    )
    enforce_runtime()  # must not raise on the live interpreter


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.negative
@pytest.mark.req("NF-006")
@pytest.mark.parametrize("bad", [(3, 10), (3, 11), (3, 12), (3, 12, 13)])
def test_older_python_fails_closed(bad: tuple[int, ...]) -> None:
    assert is_supported_runtime(bad) is False
    with pytest.raises(RuntimeError, match=r"requires Python >= 3\.13"):
        enforce_runtime(bad)


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("NF-006")
@pytest.mark.parametrize("ok", [(3, 13), (3, 13, 14), (3, 14), (4, 0)])
def test_new_enough_python_passes(ok: tuple[int, ...]) -> None:
    assert is_supported_runtime(ok) is True
    enforce_runtime(ok)


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("NF-006")
def test_python_version_file_is_313() -> None:
    pv = (_REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert pv.startswith("3.13"), f".python-version must pin 3.13, got {pv!r}"


@pytest.mark.UT
@pytest.mark.internal
@pytest.mark.req("NF-006")
def test_pyproject_requires_python_313() -> None:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
    assert m, "requires-python not found in pyproject.toml"
    assert ">=3.13" in m.group(1).replace(" ", ""), (
        f"requires-python must be >=3.13, got {m.group(1)!r}"
    )
    # Ruff/mypy targets must not permit an earlier normal runtime.
    assert 'target-version = "py313"' in text
    assert 'python_version = "3.13"' in text
