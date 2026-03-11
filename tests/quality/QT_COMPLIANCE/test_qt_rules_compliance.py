"""QT rules compliance checks (RC-01 .. RC-10).

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Static compliance checks for RULES.md guardrails.
Requirements: FR1.3, FR1.19, NF1.7
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.1
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
import re

from ._helpers import Violation, format_violations, ratio, read_text, rel


def _path_allowed(path: str, allowed: set[str]) -> bool:
    return path in allowed


def test_no_hardcoded_urls(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    pattern = re.compile(r"(https?://|localhost|127\.0\.0\.1)")
    allow_paths = set(allowlist["hardcoded_url_path_allowlist"])
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        if _path_allowed(path_rel, allow_paths):
            continue
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=path_rel,
                        line=idx,
                        message="hardcoded URL/host literal",
                    )
                )
    assert not violations, "Hardcoded URL/host findings:\n" + format_violations(
        violations
    )


def test_no_hardcoded_credentials(
    project_root: Path, src_python_files: list[Path]
) -> None:
    pattern = re.compile(
        r"\b(password|token|api_key|secret)\s*=\s*['\"][^'\"]+['\"]", re.I
    )
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=path_rel,
                        line=idx,
                        message="literal secret-like assignment",
                    )
                )
    assert not violations, "Hardcoded credential findings:\n" + format_violations(
        violations
    )


def test_no_direct_external_imports(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    import_re = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w\.]*)")
    tracked = {
        "requests",
        "httpx",
        "smtplib",
        "chromadb",
        "openai",
        "qdrant_client",
        "yaml",
    }
    seen: dict[str, set[str]] = defaultdict(set)
    for path in src_python_files:
        path_rel = rel(path, project_root)
        for line in read_text(path).splitlines():
            m = import_re.match(line)
            if not m:
                continue
            module = m.group(1).split(".")[0]
            if module in tracked:
                seen[module].add(path_rel)

    allow_modules = set(allowlist["external_import_multi_allowlist"])
    violations: list[str] = []
    for module, files in sorted(seen.items()):
        if len(files) > 1 and module not in allow_modules:
            violations.append(
                f"{module} imported in {len(files)} modules: {sorted(files)}"
            )
    assert not violations, "External import spread violations:\n- " + "\n- ".join(
        violations
    )


def test_no_skip_calls_in_it_at(project_root: Path) -> None:
    skip_call = "pytest." + "skip("
    violations: list[Violation] = []
    for test_dir in ("tests/integration", "tests/application"):
        for path in (project_root / test_dir).rglob("*.py"):
            for idx, line in enumerate(read_text(path).splitlines(), 1):
                if skip_call in line:
                    violations.append(
                        Violation(
                            path=rel(path, project_root),
                            line=idx,
                            message="skip call in IT/AT",
                        )
                    )
    assert not violations, "IT/AT skip usage found:\n" + format_violations(violations)


def test_no_mock_in_it_at(project_root: Path) -> None:
    pattern = re.compile(r"\b(MagicMock|MockTransport|local_mode\s*=\s*True)\b")
    violations: list[Violation] = []
    for test_dir in ("tests/integration", "tests/application"):
        for path in (project_root / test_dir).rglob("*.py"):
            for idx, line in enumerate(read_text(path).splitlines(), 1):
                if pattern.search(line):
                    violations.append(
                        Violation(
                            path=rel(path, project_root),
                            line=idx,
                            message="mock/local_mode in IT/AT",
                        )
                    )
    assert not violations, "IT/AT mock usage found:\n" + format_violations(violations)


def test_file_headers_present(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    violations: list[Violation] = []
    allow_prefixes = set(allowlist["file_header_prefix_allowlist"])
    allow_paths = set(allowlist["file_header_path_allowlist"])
    for path in src_python_files:
        path_rel = rel(path, project_root)
        if path.name == "__init__.py":
            continue
        if path_rel in allow_paths:
            continue
        if any(path_rel.startswith(prefix) for prefix in allow_prefixes):
            continue
        first = "\n".join(read_text(path).splitlines()[:10])
        if '"""' not in first or "License:" not in first:
            violations.append(
                Violation(
                    path=path_rel,
                    line=1,
                    message="missing module header/docstring with License",
                )
            )
    assert not violations, "Missing file headers:\n" + format_violations(violations)


def test_functions_have_docstrings(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    total = 0
    with_doc = 0
    for path in src_python_files:
        tree = ast.parse(read_text(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total += 1
                if ast.get_docstring(node):
                    with_doc += 1
    minimum_percent = float(allowlist["docstring_min_percent"])
    actual_ratio = ratio(with_doc, total)
    actual_percent = actual_ratio * 100.0
    assert actual_percent >= minimum_percent, (
        f"Function docstring ratio below threshold: {actual_percent:.2f}% < {minimum_percent:.2f}% "
        f"({with_doc}/{total})"
    )
