"""Markdown edit scaffolding."""

from __future__ import annotations

from typing import List, Optional


def _normalize_heading(heading: str) -> str:
    return heading.strip().lstrip("#").strip().lower()


def _find_heading_indices(lines: List[str], heading: str) -> Optional[int]:
    target = _normalize_heading(heading)
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            if _normalize_heading(line) == target:
                return idx
    return None


def md_get_section(text: str, heading: str) -> Optional[str]:
    lines = text.splitlines()
    start_idx = _find_heading_indices(lines, heading)
    if start_idx is None:
        return None
    start_level = len(lines[start_idx].lstrip().split(" ")[0])
    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if line.lstrip().startswith("#"):
            level = len(line.lstrip().split(" ")[0])
            if level <= start_level:
                end_idx = idx
                break
    return "\n".join(lines[start_idx:end_idx])


def md_set_section(text: str, heading: str, new_content: str) -> str:
    lines = text.splitlines()
    start_idx = _find_heading_indices(lines, heading)
    if start_idx is None:
        return text + "\n" + new_content
    start_level = len(lines[start_idx].lstrip().split(" ")[0])
    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if line.lstrip().startswith("#"):
            level = len(line.lstrip().split(" ")[0])
            if level <= start_level:
                end_idx = idx
                break
    updated = lines[:start_idx] + new_content.splitlines() + lines[end_idx:]
    return "\n".join(updated)
