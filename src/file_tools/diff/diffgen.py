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
file-mcp-server — file_tools/diff/diffgen.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for diff diffgen.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import difflib


def diff_text(
    original: str,
    updated: str,
    *,
    context: int = 3,
    fromfile: str = "a",
    tofile: str = "b",
) -> str:
    """Execute diff text."""
    original_lines = original.splitlines(keepends=True)
    updated_lines = updated.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        updated_lines,
        fromfile=fromfile,
        tofile=tofile,
        n=context,
    )
    return "".join(diff)


def diff_files(
    path_a: Path,
    path_b: Path,
    *,
    encoding: str = "utf-8",
    context: int = 3,
) -> str:
    """Execute diff files."""
    original = path_a.read_text(encoding=encoding)
    updated = path_b.read_text(encoding=encoding)
    return diff_text(
        original,
        updated,
        context=context,
        fromfile=path_a.as_posix(),
        tofile=path_b.as_posix(),
    )


def diff_lines(
    original: Iterable[str],
    updated: Iterable[str],
    *,
    context: int = 3,
    fromfile: str = "a",
    tofile: str = "b",
) -> List[str]:
    """Execute diff lines."""
    return list(
        difflib.unified_diff(
            list(original),
            list(updated),
            fromfile=fromfile,
            tofile=tofile,
            n=context,
        )
    )
