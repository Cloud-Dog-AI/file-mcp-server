"""Shared helpers for W25A QT compliance tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Static scanners and traceability parsers for project compliance checks.
Requirements: FR1.3, BO1.5
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.1-QT1.5
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

REQ_ID_RE = re.compile(r"\b(?:SV|BO|BR|FR|UC|CS|NF)\d+\.\d+\b")
TEST_ID_RE = re.compile(r"\b(?:UT|ST|IT|AT|QT)\d+(?:\.\d+)?\b")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class RequirementRecord:
    req_id: str
    title: str


@dataclass(frozen=True)
class DeliveryRow:
    req_id: str
    title: str
    code_refs: tuple[str, ...]
    test_refs: tuple[str, ...]
    status: str


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def line_matches(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for idx, line in enumerate(read_text(path).splitlines(), 1):
        if pattern.search(line):
            matches.append((idx, line))
    return matches


def parse_requirements(requirements_path: Path) -> list[RequirementRecord]:
    records: list[RequirementRecord] = []
    seen: set[str] = set()
    heading_re = re.compile(
        r"^###\s+((?:SV|BO|BR|FR|UC|CS|NF)\d+\.\d+)\s*:\s*(.+?)\s*$"
    )
    for line in read_text(requirements_path).splitlines():
        m = heading_re.match(line.strip())
        if not m:
            continue
        req_id = m.group(1)
        if req_id in seen:
            continue
        seen.add(req_id)
        records.append(RequirementRecord(req_id=req_id, title=m.group(2).strip()))

    if records:
        return records

    # Fallback for malformed docs: preserve first-seen order.
    req_ids: list[str] = []
    for m in REQ_ID_RE.finditer(read_text(requirements_path)):
        req_id = m.group(0)
        if req_id not in seen:
            seen.add(req_id)
            req_ids.append(req_id)
    return [RequirementRecord(req_id=req_id, title="") for req_id in req_ids]


def parse_tests_catalogue_tests_ids(tests_doc_path: Path) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for m in TEST_ID_RE.finditer(read_text(tests_doc_path)):
        test_id = m.group(0)
        if test_id not in seen:
            seen.add(test_id)
            ids.append(test_id)
    return ids


def find_req_refs(text: str) -> set[str]:
    return set(REQ_ID_RE.findall(text))


def is_comment_line(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def violation_lines(
    files: Iterable[Path],
    *,
    pattern: re.Pattern[str],
    root: Path,
    skip_comments: bool = False,
) -> list[Violation]:
    out: list[Violation] = []
    for path in files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if skip_comments and is_comment_line(line):
                continue
            if pattern.search(line):
                out.append(
                    Violation(path=rel(path, root), line=idx, message=line.strip())
                )
    return out


def format_violations(items: list[Violation]) -> str:
    if not items:
        return ""
    return "\n".join(f"- {v.path}:{v.line} :: {v.message}" for v in items)


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator
