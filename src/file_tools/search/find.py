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

"""File/content search helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Search for files and content with optional result and size limits.
Requirements: FR1.9, NF1.2, CS1.5
Tasks: T6, T18
Architecture: 6.2 Search, 7.2 Performance
Tests: UT1.5, ST1.7
Recent Change History:
- 2026-02-05: Added optional max file size filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

import re
import os

from ..limits import exceeds_max_file_size


@dataclass(frozen=True)
class SearchMatch:
    path: Path
    line_no: Optional[int]
    line: Optional[str]


def _parse_time_filter(value: str | None) -> float | None:
    """Parse RFC3339/ISO8601 timestamp filters to UTC epoch seconds."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    normalized = cleaned[:-1] + "+00:00" if cleaned.endswith("Z") else cleaned
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.timestamp()


def _within_modified_window(
    path: Path, *, modified_after_ts: float | None, modified_before_ts: float | None
) -> bool:
    """Return True when file mtime is within the optional exclusive window."""
    if modified_after_ts is None and modified_before_ts is None:
        return True
    try:
        modified_ts = path.stat().st_mtime
    except OSError:
        return False
    if modified_after_ts is not None and modified_ts <= modified_after_ts:
        return False
    if modified_before_ts is not None and modified_ts >= modified_before_ts:
        return False
    return True


def _iter_files(
    roots: Iterable[Path],
    *,
    recursive: bool = True,
    max_depth: int | None = None,
) -> Iterator[Path]:
    """Handle iter files."""
    for root in roots:
        resolved_root = root.resolve()
        if recursive:
            if max_depth is None:
                yield from (path for path in resolved_root.rglob("*") if path.is_file())
                continue
            for current_root, _, files in os.walk(resolved_root):
                current_path = Path(current_root)
                try:
                    depth = len(current_path.relative_to(resolved_root).parts)
                except ValueError:
                    continue
                if depth > max_depth:
                    continue
                for file_name in files:
                    yield current_path / file_name
        else:
            yield from (path for path in resolved_root.iterdir() if path.is_file())


def search_paths(
    query: str,
    *,
    roots: Iterable[Path],
    glob: str | None = None,
    regex: bool = False,
    max_file_mb: int | None = None,
    max_depth: int | None = None,
    modified_after: str | None = None,
    modified_before: str | None = None,
) -> List[Path]:
    """Search paths."""
    pattern = re.compile(query) if regex else None
    modified_after_ts = _parse_time_filter(modified_after)
    modified_before_ts = _parse_time_filter(modified_before)
    if (
        modified_after_ts is not None
        and modified_before_ts is not None
        and modified_after_ts >= modified_before_ts
    ):
        return []
    matches: List[Path] = []
    for path in _iter_files(roots, max_depth=max_depth):
        if glob and not path.match(glob):
            continue
        if not _within_modified_window(
            path,
            modified_after_ts=modified_after_ts,
            modified_before_ts=modified_before_ts,
        ):
            continue
        try:
            if max_file_mb is not None and exceeds_max_file_size(path, max_file_mb):
                continue
        except OSError:
            continue
        if regex:
            if pattern and pattern.search(path.as_posix()):
                matches.append(path)
        elif query in path.as_posix():
            matches.append(path)
    return matches


def search_content(
    query: str,
    *,
    roots: Iterable[Path],
    glob: str | None = None,
    regex: bool = False,
    encoding: str = "utf-8",
    max_results: int | None = None,
    max_file_mb: int | None = None,
    max_depth: int | None = None,
    modified_after: str | None = None,
    modified_before: str | None = None,
) -> List[SearchMatch]:
    """Search content."""
    pattern = re.compile(query) if regex else None
    modified_after_ts = _parse_time_filter(modified_after)
    modified_before_ts = _parse_time_filter(modified_before)
    if (
        modified_after_ts is not None
        and modified_before_ts is not None
        and modified_after_ts >= modified_before_ts
    ):
        return []
    results: List[SearchMatch] = []
    for path in _iter_files(roots, max_depth=max_depth):
        if glob and not path.match(glob):
            continue
        if not _within_modified_window(
            path,
            modified_after_ts=modified_after_ts,
            modified_before_ts=modified_before_ts,
        ):
            continue
        try:
            if max_file_mb is not None and exceeds_max_file_size(path, max_file_mb):
                continue
            with path.open("r", encoding=encoding, errors="replace") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if regex:
                        if pattern and pattern.search(line):
                            results.append(
                                SearchMatch(
                                    path=path, line_no=line_no, line=line.rstrip("\n")
                                )
                            )
                    else:
                        if query in line:
                            results.append(
                                SearchMatch(
                                    path=path, line_no=line_no, line=line.rstrip("\n")
                                )
                            )
                    if max_results is not None and len(results) >= max_results:
                        return results
        except (OSError, UnicodeError):
            continue
    return results
