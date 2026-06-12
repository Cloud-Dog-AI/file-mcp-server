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

"""QT traceability checks for REQUIREMENTS <-> TESTS <-> CODE.
import pytest

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Enforces requirement/test/code linkage and delivery matrix generation.
Requirements: BO1.5, FR1.3
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.5
"""

from __future__ import annotations

from pathlib import Path

from ._helpers import (
    DeliveryRow,
    find_req_refs,
    parse_requirements,
    parse_tests_catalogue_tests_ids,
    ratio,
    read_text,
)


def _status(has_code: bool, has_test: bool) -> str:
    if has_code and has_test:
        return "DELIVERED"
    if has_code and not has_test:
        return "UNTESTABLE"
    if not has_code and has_test:
        return "PARTIAL"
    return "NOT_STARTED"


def _collect_refs(project_root: Path) -> tuple[list[DeliveryRow], list[str], list[str]]:
    requirements = parse_requirements(project_root / "docs/REQUIREMENTS.md")
    tests_doc_text = read_text(project_root / "docs/TESTS.md")

    src_refs: dict[str, list[str]] = {req.req_id: [] for req in requirements}
    test_refs: dict[str, list[str]] = {req.req_id: [] for req in requirements}

    for path in sorted((project_root / "src").rglob("*.py")):
        text = read_text(path)
        refs = find_req_refs(text)
        for req in refs:
            if req in src_refs:
                src_refs[req].append(path.relative_to(project_root).as_posix())

    for path in sorted((project_root / "tests").rglob("*.py")):
        rel_path = path.relative_to(project_root).as_posix()
        if rel_path == "tests/quality/QT_COMPLIANCE/conftest.py":
            # Allowlist metadata includes backlog requirement IDs; exclude from coverage maths.
            continue
        text = read_text(path)
        refs = find_req_refs(text)
        for req in refs:
            if req in test_refs:
                test_refs[req].append(rel_path)

    for req in requirements:
        if (
            req.req_id in tests_doc_text
            and "docs/TESTS.md" not in test_refs[req.req_id]
        ):
            test_refs[req.req_id].append("docs/TESTS.md")

    rows: list[DeliveryRow] = []
    missing_tests: list[str] = []
    missing_code: list[str] = []

    for req in requirements:
        code = tuple(sorted(set(src_refs[req.req_id])))
        tests = tuple(sorted(set(test_refs[req.req_id])))
        if not tests:
            missing_tests.append(req.req_id)
        if not code:
            missing_code.append(req.req_id)
        rows.append(
            DeliveryRow(
                req_id=req.req_id,
                title=req.title,
                code_refs=code,
                test_refs=tests,
                status=_status(bool(code), bool(tests)),
            )
        )
    return rows, missing_tests, missing_code
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_all_requirements_have_tests(
    project_root: Path, allowlist: dict[str, object]
) -> None:
    _, missing_tests, _ = _collect_refs(project_root)
    allowed = set(allowlist["traceability_missing_tests"])
    unresolved = sorted(req for req in missing_tests if req not in allowed)
    assert not unresolved, "Requirements missing tests:\n- " + "\n- ".join(unresolved)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_all_tests_have_requirements(
    project_root: Path, allowlist: dict[str, object]
) -> None:
    tests_doc = read_text(project_root / "docs/TESTS.md")
    test_ids = parse_tests_catalogue_tests_ids(project_root / "docs/TESTS.md")
    orphan: list[str] = []
    for test_id in test_ids:
        prefix = "".join(ch for ch in test_id if ch.isalpha())
        if prefix in set(allowlist["traceability_orphan_test_ids_prefix_allowlist"]):
            continue
        for line in tests_doc.splitlines():
            if test_id in line:
                if not find_req_refs(line):
                    orphan.append(test_id)
                break

    orphan = sorted(set(orphan))
    assert not orphan, (
        "Tests without requirement references in docs/TESTS.md:\n- "
        + "\n- ".join(orphan)
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_all_requirements_have_code(
    project_root: Path, allowlist: dict[str, object]
) -> None:
    _, _, missing_code = _collect_refs(project_root)
    allowed = set(allowlist["traceability_missing_code"])
    unresolved = sorted(req for req in missing_code if req not in allowed)
    assert not unresolved, "Requirements missing code references:\n- " + "\n- ".join(
        unresolved
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_delivery_matrix_complete(
    project_root: Path, allowlist: dict[str, object]
) -> None:
    rows, _, _ = _collect_refs(project_root)
    lines = ["| Req ID | Title | Code | Test | Status |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append(
            "| {rid} | {title} | {code} | {test} | {status} |".format(
                rid=row.req_id,
                title=row.title.replace("|", "\\|"),
                code=(", ".join(row.code_refs) if row.code_refs else "-"),
                test=(", ".join(row.test_refs) if row.test_refs else "-"),
                status=row.status,
            )
        )

    out = Path("/tmp/w25a_qt_delivery_matrix.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exempt = set(allowlist["traceability_missing_code"]) | set(
        allowlist["traceability_missing_tests"]
    )
    fr_rows = [
        row for row in rows if row.req_id.startswith("FR") and row.req_id not in exempt
    ]
    delivered = sum(1 for row in fr_rows if row.status == "DELIVERED")
    delivered_ratio = ratio(delivered, len(fr_rows))

    assert delivered_ratio >= 0.80, (
        f"FR delivered ratio below 80% in non-allowlisted set: {delivered_ratio:.2%} "
        f"({delivered}/{len(fr_rows)}). Matrix: {out}"
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_orphan_test_files(project_root: Path, allowlist: dict[str, object]) -> None:
    tests_doc = read_text(project_root / "docs/TESTS.md")
    missing: list[str] = []
    allowed_missing = set(allowlist["traceability_missing_test_file_refs"])

    for path in sorted((project_root / "tests").rglob("test_*.py")):
        rel_path = path.relative_to(project_root).as_posix()
        if "tests/quality/QT_COMPLIANCE" in rel_path:
            continue
        if rel_path in tests_doc or path.name in tests_doc:
            continue
        if rel_path in allowed_missing:
            continue
        missing.append(rel_path)

    assert not missing, "Test files missing from docs/TESTS.md:\n- " + "\n- ".join(
        missing
    )
