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

"""Tool reuse tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests ensuring file_tools helpers are usable without server runtime.
Requirements: FR1.24, BO1.3
Tasks: T17
Architecture: Separation rule
Tests: UT1.18
Recent Change History:
- 2026-02-05: Add tool reuse tests with config-driven roots.
"""


from __future__ import annotations
import pytest

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.diff import diff_text
from file_tools.edit import replace_regex
from file_tools.io import read_text, write_text
from file_tools.validate import validate_json


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
@pytest.mark.req("FR-1.24")


def test_file_tools_helpers_reusable(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    path = root / "note.txt"
    write_text(path, "alpha beta", encoding="utf-8")

    updated = replace_regex(read_text(path, encoding="utf-8"), r"beta", "gamma")
    assert updated.changed
    write_text(path, updated.text, encoding="utf-8")
    assert read_text(path, encoding="utf-8") == "alpha gamma"

    diff = diff_text("alpha\n", "beta\n", fromfile="a.txt", tofile="b.txt")
    assert "-alpha" in diff
    assert "+beta" in diff

    assert validate_json('{"a": 1}').valid
