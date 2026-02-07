"""Filesystem utility tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for filesystem operations using config-driven scope roots.
Requirements: FR1.7, FR1.8, NF1.1
Tasks: T5
Architecture: 6.1 Core file operations
Tests: UT1.4
Recent Change History:
- 2026-02-05: Align tests to config/env precedence for scoped roots.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.config_helpers import build_profile
from file_tools.io import (
    atomic_write,
    copy_file,
    delete_file,
    list_dir,
    move_file,
    read_text,
    write_text,
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


def test_atomic_write_and_read(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "notes.txt"
    atomic_write(target, b"hello")
    assert read_text(target) == "hello"


def test_atomic_write_respects_overwrite(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "notes.txt"
    atomic_write(target, b"first")
    with pytest.raises(FileExistsError):
        atomic_write(target, b"second", overwrite=False)


def test_write_text_and_copy_move(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    src = root / "src.txt"
    dst = root / "dst.txt"
    moved = root / "moved.txt"

    write_text(src, "data")
    copy_file(src, dst)
    assert read_text(dst) == "data"

    move_file(src, moved)
    assert not src.exists()
    assert read_text(moved) == "data"


def test_delete_file_missing_ok(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "missing.txt"
    delete_file(target, missing_ok=True)


def test_list_dir(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    (root / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")
    entries = list_dir(root)
    assert len(entries) == 2
    assert {path.name for path in entries} == {"a.txt", "b.txt"}
