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

"""QT migration completeness checks.
import pytest

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Detects leftover bespoke implementations that should be platform-package based.
Requirements: FR1.2, FR1.3, FR1.5, FR1.19
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.4
"""

from __future__ import annotations

from pathlib import Path
import re

from ._helpers import Violation, format_violations, read_text, rel
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_yaml_safe_load_for_config(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    allow_paths = set(allowlist["yaml_safe_load_data_allowlist"])
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        if path_rel in allow_paths:
            continue
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if "yaml.safe_load" in line or "yaml.load(" in line:
                violations.append(
                    Violation(
                        path=path_rel,
                        line=idx,
                        message="yaml load in non-allowlisted module",
                    )
                )
    assert not violations, "yaml.safe_load migration violations:\n" + format_violations(
        violations
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_raw_fastapi(project_root: Path, src_python_files: list[Path]) -> None:
    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if "FastAPI(" in line:
                violations.append(
                    Violation(
                        path=rel(path, project_root),
                        line=idx,
                        message="direct FastAPI construction",
                    )
                )
    assert not violations, "Raw FastAPI usage found:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_bespoke_auth(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    allow_paths = set(allowlist["bespoke_auth_allowlist"])
    pattern = re.compile(r"\b(APIKeyHeader|verify_token\s*\()")
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        if path_rel in allow_paths:
            continue
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=path_rel,
                        line=idx,
                        message="possible bespoke auth implementation",
                    )
                )
    assert not violations, "Bespoke auth findings:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_os_environ_for_config(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    allow_paths = set(allowlist["os_env_allowlist"])
    getenv_token = r"os" + r"\.getenv\s*\("
    environ_token = r"os" + r"\.environ\b"
    pattern = re.compile(rf"\b{getenv_token}|\b{environ_token}")
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        if path_rel in allow_paths:
            continue
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=path_rel, line=idx, message="direct os env config access"
                    )
                )
    assert not violations, (
        "direct env access migration findings:\n" + format_violations(violations)
    )
