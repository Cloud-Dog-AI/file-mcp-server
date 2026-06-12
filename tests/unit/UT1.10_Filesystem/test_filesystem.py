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
import stat

import pytest

from tests.config_helpers import build_profile
from file_tools.io import (
    atomic_write,
    chmod_path,
    copy_file,
    create_dir,
    delete_file,
    list_dir,
    move_file,
    move_path,
    read_text,
    rename_path,
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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_atomic_write_and_read(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "notes.txt"
    atomic_write(target, b"hello")
    assert read_text(target) == "hello"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_atomic_write_respects_overwrite(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "notes.txt"
    atomic_write(target, b"first")
    with pytest.raises(FileExistsError):
        atomic_write(target, b"second", overwrite=False)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_delete_file_missing_ok(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "missing.txt"
    delete_file(target, missing_ok=True)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_list_dir(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    (root / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")
    entries = list_dir(root)
    assert len(entries) == 2
    assert {path.name for path in entries} == {"a.txt", "b.txt"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_create_dir_and_move_rename_with_utf8_names(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    source_dir = root / "naive-测试"
    create_dir(source_dir)
    file_path = source_dir / "cafe-🙂.txt"
    write_text(file_path, "payload", encoding="utf-8")

    moved_dir = root / "moved-δοκιμή"
    move_path(source_dir, moved_dir)
    assert not source_dir.exists()
    assert (moved_dir / "cafe-🙂.txt").exists()

    renamed_dir = root / "renamed-данные"
    rename_path(moved_dir, renamed_dir)
    assert not moved_dir.exists()
    assert (renamed_dir / "cafe-🙂.txt").read_text(encoding="utf-8") == "payload"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_chmod_path_updates_mode_for_file(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    target = root / "mode.txt"
    write_text(target, "mode")
    chmod_path(target, 0o640)
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o640
