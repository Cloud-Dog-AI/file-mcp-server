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

"""QT platform package adoption checks.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Verifies cloud_dog package adoption and bespoke-implementation drift.
Requirements: FR1.2, FR1.3, FR1.5, FR1.19
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.2
"""


from __future__ import annotations
import pytest

from pathlib import Path
import re

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]

from ._helpers import Violation, format_violations, read_text, rel


def _any_src_import(project_root: Path, package: str) -> bool:
    pattern = re.compile(
        rf"^\s*(?:from|import)\s+{re.escape(package)}(?:\.|\s|$)", re.M
    )
    for path in (project_root / "src").rglob("*.py"):
        if pattern.search(read_text(path)):
            return True
    return False
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_config_uses_cloud_dog_config(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    assert _any_src_import(project_root, "cloud_dog_config"), (
        "cloud_dog_config import missing in src/"
    )

    allow_paths = set(allowlist["yaml_safe_load_data_allowlist"])
    violations: list[Violation] = []
    for path in src_python_files:
        path_rel = rel(path, project_root)
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if "yaml.safe_load" not in line and "yaml.load" not in line:
                continue
            if path_rel in allow_paths:
                continue
            violations.append(
                Violation(
                    path=path_rel,
                    line=idx,
                    message="yaml load outside approved data-file parser",
                )
            )
    assert not violations, "Potential bespoke config loading:\n" + format_violations(
        violations
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_logging_uses_cloud_dog_logging(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    assert _any_src_import(project_root, "cloud_dog_logging"), (
        "cloud_dog_logging import missing in src/"
    )
    allow_paths = set(allowlist["logging_call_allowlist"])
    pattern = re.compile(r"logging\.(?:getLogger|basicConfig)\(")
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
                        message="stdlib logging bootstrap/getLogger usage",
                    )
                )
    assert not violations, "Logging adoption violations:\n" + format_violations(
        violations
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_api_uses_cloud_dog_api_kit(
    project_root: Path, src_python_files: list[Path]
) -> None:
    # API server project heuristic: file_mcp_server runtime entrypoint present.
    is_api_server = (project_root / "src/file_mcp_server/server.py").exists()
    if not is_api_server:
        return
    assert _any_src_import(project_root, "cloud_dog_api_kit"), (
        "cloud_dog_api_kit import missing"
    )

    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if "FastAPI(" in line:
                violations.append(
                    Violation(
                        path=rel(path, project_root),
                        line=idx,
                        message="direct FastAPI() usage",
                    )
                )
    assert not violations, "Direct FastAPI construction found:\n" + format_violations(
        violations
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_auth_uses_cloud_dog_idam(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    is_api_server = (project_root / "src/file_mcp_server/server.py").exists()
    if not is_api_server:
        return
    assert _any_src_import(project_root, "cloud_dog_idam"), (
        "cloud_dog_idam import missing"
    )
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
                        message="possible bespoke auth handling",
                    )
                )
    assert not violations, "Auth adoption violations:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_bespoke_db_access(project_root: Path, src_python_files: list[Path]) -> None:
    pattern = re.compile(r"\b(sqlite3\.connect|create_engine\s*\()")
    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=rel(path, project_root),
                        line=idx,
                        message="direct DB driver/engine usage",
                    )
                )
    assert not violations, "Bespoke DB usage found:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_bespoke_llm_calls(project_root: Path, src_python_files: list[Path]) -> None:
    pattern = re.compile(r"\b(openai\.OpenAI\s*\(|ollama\.chat\s*\()")
    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=rel(path, project_root),
                        line=idx,
                        message="direct LLM client call",
                    )
                )
    assert not violations, "Bespoke LLM usage found:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_no_bespoke_vdb_calls(project_root: Path, src_python_files: list[Path]) -> None:
    pattern = re.compile(r"\b(chromadb\.Client\s*\(|qdrant_client\.QdrantClient\s*\()")
    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=rel(path, project_root),
                        line=idx,
                        message="direct VDB client call",
                    )
                )
    assert not violations, "Bespoke VDB usage found:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_pyproject_declares_platform_packages(project_root: Path) -> None:
    content = read_text(project_root / "pyproject.toml")
    if tomllib is not None:
        data = tomllib.loads(content)
        deps = set(data["project"].get("dependencies", []))
        dep_names = {
            dep.split(";")[0].split(">=")[0].split("==")[0].strip() for dep in deps
        }
    else:
        dep_names = set(
            re.findall(r"\"(cloud_dog_[a-z_]+)(?:[<>=].*?)?\"", content, flags=re.I)
        )

    expected = {"cloud_dog_config", "cloud_dog_logging"}
    if (project_root / "src/file_mcp_server/server.py").exists():
        expected.update({"cloud_dog_api_kit", "cloud_dog_idam"})
    if (project_root / "src/file_mcp_server/db").exists():
        expected.add("cloud_dog_db")

    missing = sorted(pkg for pkg in expected if pkg not in dep_names)
    assert not missing, f"Missing platform dependencies in pyproject.toml: {missing}"
