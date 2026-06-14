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

"""QT vault/config contract checks.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Static checks for secrets hygiene and env/vault contract alignment.
Requirements: FR1.3, FR1.5, CS1.1
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.3
"""


from __future__ import annotations
import pytest

from pathlib import Path
import re

from ._helpers import Violation, format_violations, read_text, rel


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in read_text(path).splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _secret_assignments(text: str) -> list[str]:
    findings: list[str] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key_upper = key.upper()
        if not any(
            token in key_upper
            for token in ("PASSWORD", "TOKEN", "SECRET", "API_KEY", "ACCESS_KEY")
        ):
            continue
        val = value.strip().strip('"').strip("'")
        if not val:
            continue
        if val.startswith("${"):
            continue
        findings.append(raw)
    return findings
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_defaults_yaml_exists(project_root: Path) -> None:
    assert (project_root / "defaults.yaml").exists(), "defaults.yaml is missing"
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_defaults_yaml_no_secrets(project_root: Path) -> None:
    content = read_text(project_root / "defaults.yaml")
    secret_like = _secret_assignments(content)
    assert not secret_like, (
        "defaults.yaml contains secret-like assignments:\n- " + "\n- ".join(secret_like)
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_config_yaml_no_secrets(project_root: Path) -> None:
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        return
    content = read_text(config_path)
    secret_like = _secret_assignments(content)
    assert not secret_like, (
        "config.yaml contains secret-like assignments:\n- " + "\n- ".join(secret_like)
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_env_files_use_vault_expressions(project_root: Path) -> None:
    env_targets = [
        project_root / "tests/env-IT-local-docker",
        project_root / "tests/env-AT-local-docker",
        project_root / "tests/env-IT-local-server",
        project_root / "tests/env-AT-local-server",
    ]
    key_allowlist = {
        "FILE_MCP_API_KEY_PRIMARY",
        "FILE_MCP_API_KEY_SECONDARY",
        "TEST_A2A_API_KEY",
        "FILE_MCP_S3_BUCKET",
        "FILE_MCP_S3_REGION",
        "FILE_MCP_S3_PREFIX",
        "FILE_MCP_FTP_BASE_DIR",
        "FILE_MCP_FTP_USE_TLS",
        "FILE_MCP_GDRIVE_USER_EMAIL",
        "FILE_MCP_GDRIVE_FOLDER_ID",
        "FILE_MCP_GDRIVE_FOLDER_URL",
        "FILE_MCP_RUN_GOOGLE_LIVE_TESTS",
        "FILE_MCP_RUN_GDRIVE_LIVE_TEST",
        # Local tier uses sqlite DB path during static/UT execution.
        "CLOUD_DOG__DB__DIALECT",
        "CLOUD_DOG__DB__DATABASE",
        # Local-server FTP loopback target is expected in non-remote runs.
        "FILE_MCP_FTP_HOST",
        "FILE_MCP_FTP_PORT",
    }
    candidate_key_re = re.compile(
        r"^(FILE_MCP_(S3|WEBDAV|FTP|GDRIVE)_|CLOUD_DOG__DB__)"
    )

    violations: list[str] = []
    for env_path in env_targets:
        if not env_path.exists():
            continue
        env_data = _parse_env(env_path)
        for key, value in sorted(env_data.items()):
            if not candidate_key_re.match(key):
                continue
            if key in key_allowlist:
                continue
            if not value:
                continue
            if value.startswith("${vault.dev.") and value.endswith("}"):
                continue
            violations.append(f"{env_path.name}:{key}={value}")

    assert not violations, (
        "Credential env vars without vault expressions:\n- " + "\n- ".join(violations)
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_no_secrets_in_source(project_root: Path, src_python_files: list[Path]) -> None:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----"),
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    ]
    violations: list[Violation] = []
    for path in src_python_files:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            for pattern in patterns:
                if pattern.search(line):
                    violations.append(
                        Violation(
                            path=rel(path, project_root),
                            line=idx,
                            message="possible embedded secret",
                        )
                    )
                    break
    assert not violations, "Possible secrets in src/:\n" + format_violations(violations)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-1.3")


def test_env_files_exist_per_tier(project_root: Path) -> None:
    expected = [
        "tests/env-UT-local-docker",
        "tests/env-ST-local-docker",
        "tests/env-IT-local-docker",
        "tests/env-AT-local-docker",
        "tests/env-UT-local-server",
        "tests/env-ST-local-server",
        "tests/env-IT-local-server",
        "tests/env-AT-local-server",
    ]
    missing = [path for path in expected if not (project_root / path).exists()]
    assert not missing, f"Missing tier env files: {missing}"
