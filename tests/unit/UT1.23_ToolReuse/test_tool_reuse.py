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
