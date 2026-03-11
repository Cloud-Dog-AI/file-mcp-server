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
