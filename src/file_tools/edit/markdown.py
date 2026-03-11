"""
file-mcp-server — file_tools/edit/markdown.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for edit markdown.py.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from file_tools.adapters import safe_dump as yaml_safe_dump
from file_tools.adapters import safe_load as yaml_safe_load


def _normalize_heading(heading: str) -> str:
    """Handle normalize heading."""
    return heading.strip().lstrip("#").strip().lower()


def _slugify(text: str) -> str:
    """Handle slugify."""
    base = text.strip().lower()
    base = re.sub(r"[^\w\s-]", "", base)
    return re.sub(r"[\s_]+", "-", base).strip("-")


def _heading_title(line: str) -> str:
    """Handle heading title."""
    return line.lstrip().lstrip("#").strip()


def _heading_level(line: str) -> int:
    """Handle heading level."""
    return len(line.lstrip().split(" ")[0])


def _frontmatter_bounds(lines: List[str]) -> tuple[int, int] | None:
    """Handle frontmatter bounds."""
    if len(lines) < 3 or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return 0, idx
    return None


def _find_heading_indices(lines: List[str], heading: str | List[str]) -> Optional[int]:
    """Handle find heading indices."""
    if isinstance(heading, list):
        if not heading:
            return None
        path = [_normalize_heading(item) for item in heading]
        idx = 0
        parent_level = 0
        for target in path:
            found_idx = None
            for cand in range(idx, len(lines)):
                line = lines[cand]
                if not line.lstrip().startswith("#"):
                    continue
                title = _heading_title(line)
                normalized = _normalize_heading(title)
                slug = _slugify(title)
                level = _heading_level(line)
                if level <= parent_level:
                    continue
                if normalized == target or slug == _slugify(target):
                    found_idx = cand
                    parent_level = level
                    idx = cand + 1
                    break
            if found_idx is None:
                return None
        return found_idx

    target = heading
    is_anchor = target.strip().startswith("#")
    normalized_target = _normalize_heading(target.lstrip("#") if is_anchor else target)
    slug_target = _slugify(target.lstrip("#") if is_anchor else target)
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            title = _heading_title(line)
            normalized = _normalize_heading(title)
            slug = _slugify(title)
            if normalized == normalized_target or slug == slug_target:
                return idx
    return None


def md_get_section(text: str, heading: str | List[str]) -> Optional[str]:
    """Execute md get section."""
    lines = text.splitlines()
    start_idx = _find_heading_indices(lines, heading)
    if start_idx is None:
        return None
    start_level = _heading_level(lines[start_idx])
    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if line.lstrip().startswith("#"):
            level = _heading_level(line)
            if level <= start_level:
                end_idx = idx
                break
    return "\n".join(lines[start_idx:end_idx])


def md_set_section(text: str, heading: str | List[str], new_content: str) -> str:
    """Execute md set section."""
    lines = text.splitlines()
    start_idx = _find_heading_indices(lines, heading)
    if start_idx is None:
        return text + "\n" + new_content
    start_level = _heading_level(lines[start_idx])
    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if line.lstrip().startswith("#"):
            level = _heading_level(line)
            if level <= start_level:
                end_idx = idx
                break
    updated = lines[:start_idx] + new_content.splitlines() + lines[end_idx:]
    return "\n".join(updated)


def _deep_merge(base: Any, incoming: Any) -> Any:
    """Handle deep merge."""
    if isinstance(base, dict) and isinstance(incoming, dict):
        merged = dict(base)
        for key, value in incoming.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return incoming


def md_set_frontmatter(text: str, updates: dict[str, Any]) -> str:
    """Execute md set frontmatter."""
    if not isinstance(updates, dict):
        raise ValueError("updates must be a mapping")
    lines = text.splitlines()
    bounds = _frontmatter_bounds(lines)
    if bounds is None:
        merged = updates
        content_lines = lines
    else:
        start, end = bounds
        frontmatter_block = "\n".join(lines[start + 1 : end]).strip()
        current = yaml_safe_load(frontmatter_block) if frontmatter_block else {}
        if current is None:
            current = {}
        if not isinstance(current, dict):
            raise ValueError("frontmatter must be a mapping")
        merged = _deep_merge(current, updates)
        content_lines = lines[end + 1 :]
    fm_yaml = yaml_safe_dump(merged, sort_keys=False).rstrip()
    body = "\n".join(content_lines).lstrip("\n")
    if body:
        return f"---\n{fm_yaml}\n---\n{body}"
    return f"---\n{fm_yaml}\n---\n"
