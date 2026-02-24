"""POSIX portability tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for POSIX path utilities and safe joins.
Requirements: FR1.25, NF1.5
Tasks: T17
Architecture: 7. Non-Functional Requirements
Tests: UT1.19
Recent Change History:
- 2026-02-05: Align POSIX tests to config-driven roots.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.config_helpers import build_profile
from file_tools import (
    filter_posix_paths,
    is_posix_path,
    normalize_path,
    require_relative,
    safe_join,
    to_posix,
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


def test_is_posix_path() -> None:
    assert is_posix_path("/tmp/alpha")
    assert not is_posix_path("C:\\temp\\alpha")


def test_normalize_and_to_posix(tmp_path: Path) -> None:
    path = normalize_path(tmp_path / "alpha")
    assert path.is_absolute()
    assert "/" in to_posix(path)


def test_safe_join(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    joined = safe_join(root, "sub", "file.txt")
    assert joined == (root / "sub" / "file.txt").resolve()

    with pytest.raises(ValueError):
        safe_join(root, "..", "escape")


def test_require_relative() -> None:
    require_relative(Path("relative.txt"))
    with pytest.raises(ValueError):
        require_relative(Path("/abs"))


def test_filter_posix_paths(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    paths = [root / "a.txt", Path("C:\\bad\\path")]
    filtered = filter_posix_paths(paths)
    assert root / "a.txt" in filtered
