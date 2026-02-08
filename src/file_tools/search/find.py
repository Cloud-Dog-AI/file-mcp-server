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


def _iter_files(
    roots: Iterable[Path],
    *,
    recursive: bool = True,
    max_depth: int | None = None,
) -> Iterator[Path]:
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
) -> List[Path]:
    pattern = re.compile(query) if regex else None
    matches: List[Path] = []
    for path in _iter_files(roots, max_depth=max_depth):
        if glob and not path.match(glob):
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
) -> List[SearchMatch]:
    pattern = re.compile(query) if regex else None
    results: List[SearchMatch] = []
    for path in _iter_files(roots, max_depth=max_depth):
        if glob and not path.match(glob):
            continue
        try:
            if max_file_mb is not None and exceeds_max_file_size(path, max_file_mb):
                continue
            with path.open("r", encoding=encoding, errors="replace") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if regex:
                        if pattern and pattern.search(line):
                            results.append(SearchMatch(path=path, line_no=line_no, line=line.rstrip("\n")))
                    else:
                        if query in line:
                            results.append(SearchMatch(path=path, line_no=line_no, line=line.rstrip("\n")))
                    if max_results is not None and len(results) >= max_results:
                        return results
        except (OSError, UnicodeError):
            continue
    return results
