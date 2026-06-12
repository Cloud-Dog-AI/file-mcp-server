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

"""Sed-like edit tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for regex/range edits with transactional apply.
Requirements: FR1.17
Tasks: T10
Architecture: 6.5.1 Sed-like edits
Tests: UT1.12
Recent Change History:
- 2026-02-05: Align sed-like tests to config-driven roots and atomic apply.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.config_helpers import build_profile
from file_tools.edit import (
    apply_edits,
    delete_matching_lines,
    insert_after_line,
    insert_before_line,
    replace_line_range,
    replace_regex,
)


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
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_replace_regex(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "doc.txt"
    path.write_text("alpha beta", encoding="utf-8")
    result = replace_regex(path.read_text(encoding="utf-8"), r"beta", "gamma")
    assert result.changed
    path.write_text(result.text, encoding="utf-8")
    assert path.read_text(encoding="utf-8") == "alpha gamma"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_insert_before_after_line(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "lines.txt"
    path.write_text("one\ntwo\nthree", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    before = insert_before_line(text, 2, "insert")
    after = insert_after_line(text, 2, "insert")

    assert before.text.splitlines()[1] == "insert"
    assert after.text.splitlines()[2] == "insert"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_delete_matching_lines(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "delete.txt"
    path.write_text("one\nremove\nthree", encoding="utf-8")
    result = delete_matching_lines(path.read_text(encoding="utf-8"), r"remove")
    assert result.changed
    assert "remove" not in result.text
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_replace_line_range(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "range.txt"
    path.write_text("one\ntwo\nthree", encoding="utf-8")
    result = replace_line_range(path.read_text(encoding="utf-8"), 2, 2, ["TWO"])
    assert result.changed
    assert result.text.splitlines()[1] == "TWO"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_insert_invalid_line_raises() -> None:
    with pytest.raises(IndexError):
        insert_before_line("one", 3, "bad")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_apply_edits_atomic_on_error(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "atomic.txt"
    path.write_text("one\ntwo\nthree", encoding="utf-8")
    original = path.read_text(encoding="utf-8")

    edits = [
        lambda text: replace_regex(text, r"two", "TWO"),
        lambda text: insert_before_line(text, 10, "bad"),
    ]
    result = apply_edits(original, edits)
    assert not result.changed
    assert result.text == original
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_apply_edits_success(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "apply.txt"
    path.write_text("one\ntwo\nthree", encoding="utf-8")
    original = path.read_text(encoding="utf-8")

    edits = [
        lambda text: replace_regex(text, r"two", "TWO"),
        lambda text: insert_after_line(text, 2, "insert"),
    ]
    result = apply_edits(original, edits)
    assert result.changed
    assert "TWO" in result.text
    assert "insert" in result.text
