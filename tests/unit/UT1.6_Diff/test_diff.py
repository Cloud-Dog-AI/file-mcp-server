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

"""Diff utility tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for diff generation and meld availability handling.
Requirements: FR1.11, FR1.12
Tasks: T8
Architecture: 6.4 Diff and Meld
Tests: UT1.7, UT1.8
Recent Change History:
- 2026-02-05: Align diff tests to config-driven roots and meld warnings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.config_helpers import build_profile
from file_tools.diff import diff_files, diff_text, launch_meld, meld_available


def _scoped_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    defaults_yaml = """
profiles:
  default:
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {"FILE_MCP_ROOT": str(root)}
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return Path(profile.scope.roots[0])
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_diff_text_contains_changes() -> None:
    diff = diff_text("alpha\n", "beta\n", fromfile="a.txt", tofile="b.txt")
    assert "-alpha" in diff
    assert "+beta" in diff
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_diff_files(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path_a = root / "a.txt"
    path_b = root / "b.txt"
    path_a.write_text("one\n")
    path_b.write_text("two\n")

    diff = diff_files(path_a, path_b)
    assert "-one" in diff
    assert "+two" in diff
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_meld_available_returns_bool() -> None:
    result = meld_available()
    assert isinstance(result, bool)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-003")


def test_meld_unavailable_returns_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _scoped_root(tmp_path)
    path_a = root / "a.txt"
    path_b = root / "b.txt"
    path_a.write_text("one")
    path_b.write_text("two")

    monkeypatch.setattr("file_tools.diff.meld.which", lambda _: None)
    ok, message = launch_meld(path_a, path_b)
    assert ok is False
    assert "not available" in message
