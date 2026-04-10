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

"""Fixtures for W25A compliance quality tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Shared fixtures and allowlist for static compliance scans.
Requirements: FR1.3, BO1.5
Tasks: W25A
Architecture: Compliance quality gates
Tests: QT1.1-QT1.5
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ._helpers import py_files


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    return project_root / "src"


@pytest.fixture(scope="session")
def src_python_files(src_dir: Path) -> list[Path]:
    return py_files(src_dir)


@pytest.fixture(scope="session")
def test_python_files(project_root: Path) -> list[Path]:
    return py_files(project_root / "tests")


@pytest.fixture(scope="session")
def allowlist() -> dict[str, object]:
    return {
        # W25A-B hardcoded host/URL migration completed.
        "hardcoded_url_path_allowlist": set(),
        # W25A-B import centralisation completed in file_tools.adapters.
        "external_import_multi_allowlist": set(),
        # W25A-B docstring/header remediation target.
        "docstring_min_percent": 80.0,
        "file_header_prefix_allowlist": set(),
        "file_header_path_allowlist": set(),
        # Runtime logger instance is used for middleware operational logging.
        "logging_call_allowlist": {
            "src/file_mcp_server/server_runtime.py",
        },
        # Safe-load in these modules parses user data payloads, not app config files.
        "yaml_safe_load_data_allowlist": {
            "src/file_tools/adapters/yaml_codec.py",
            "src/file_tools/edit/jsonyaml.py",
            "src/file_tools/edit/markdown.py",
            "src/file_tools/validate/validators.py",
        },
        # Runtime bootstrap and adapter shims still read process env.
        "os_env_allowlist": {
            "src/file_mcp_server/main.py",
            "src/file_mcp_server/server_runtime.py",
            "src/file_mcp_server/db/runtime.py",
        },
        # IDAM adapter exposes verify_token methods as integration point to cloud_dog_idam.
        "bespoke_auth_allowlist": {
            "src/file_mcp_server/auth.py",
            "src/file_mcp_server/server_runtime.py",
        },
        # Traceability is enforced without missing-test/missing-code waivers.
        "traceability_missing_tests": set(),
        "traceability_missing_code": set(),
        # Orphan catalogue IDs are not waived; docs/TESTS.md must carry requirement refs inline.
        "traceability_orphan_test_ids_prefix_allowlist": set(),
        "traceability_missing_test_file_refs": set(),
    }
