"""
file-mcp-server — file_tools/edit/sedlike.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for edit sedlike.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import re


@dataclass(frozen=True)
class EditResult:
    text: str
    changed: bool


def apply_edits(text: str, edits: Iterable[Callable[[str], EditResult]]) -> EditResult:
    """Execute apply edits."""
    current = text
    changed = False
    try:
        for edit in edits:
            result = edit(current)
            current = result.text
            changed = changed or result.changed
    except Exception:
        return EditResult(text=text, changed=False)
    return EditResult(text=current, changed=changed)


def replace_regex(text: str, pattern: str, repl: str, *, count: int = 0) -> EditResult:
    """Execute replace regex."""
    updated, replacements = re.subn(pattern, repl, text, count=count)
    return EditResult(text=updated, changed=replacements > 0)


def insert_before_line(text: str, line_no: int, content: str) -> EditResult:
    """Execute insert before line."""
    lines = text.splitlines()
    if line_no < 1 or line_no > len(lines) + 1:
        raise IndexError("line_no out of range")
    idx = line_no - 1
    updated = lines[:idx] + [content] + lines[idx:]
    return EditResult(text="\n".join(updated), changed=True)


def insert_after_line(text: str, line_no: int, content: str) -> EditResult:
    """Execute insert after line."""
    lines = text.splitlines()
    if line_no < 1 or line_no > len(lines):
        raise IndexError("line_no out of range")
    idx = line_no
    updated = lines[:idx] + [content] + lines[idx:]
    return EditResult(text="\n".join(updated), changed=True)


def delete_matching_lines(text: str, pattern: str) -> EditResult:
    """Delete matching lines."""
    regex = re.compile(pattern)
    lines = text.splitlines()
    kept = [line for line in lines if not regex.search(line)]
    return EditResult(text="\n".join(kept), changed=len(kept) != len(lines))


def replace_line_range(
    text: str, start: int, end: int, replacement: Iterable[str]
) -> EditResult:
    """Execute replace line range."""
    lines = text.splitlines()
    if start < 1 or end < start or end > len(lines):
        raise IndexError("range out of bounds")
    start_idx = start - 1
    end_idx = end
    updated = lines[:start_idx] + list(replacement) + lines[end_idx:]
    return EditResult(text="\n".join(updated), changed=True)
