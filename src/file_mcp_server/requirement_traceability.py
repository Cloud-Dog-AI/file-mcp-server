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

"""Requirement traceability manifest for file-mcp-server.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Explicit requirement-to-code mapping used by QT traceability checks.
Requirements: SV1.1, SV1.2, SV1.3, SV1.4, BO1.1, BO1.2, BO1.3, BO1.4, BO1.5, BR1.1, BR1.2, BR1.3, BR1.4, BR1.5, BR1.6, FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR1.6, FR1.7, FR1.8, FR1.9, FR1.10, FR1.11, FR1.12, FR1.13, FR1.14, FR1.15, FR1.16, FR1.17, FR1.18, FR1.19, FR1.20, FR1.21, FR1.22, FR1.23, FR1.46, FR1.24, FR1.25, FR1.26, FR1.27, FR1.28, FR1.29, FR1.30, FR1.31, FR1.32, FR1.33, FR1.34, FR1.35, FR1.36, FR1.37, FR1.38, FR1.39, FR1.40, FR1.41, FR1.42, FR1.43, FR1.44, FR1.45, UC1.1, UC1.2, UC1.3, UC1.4, UC1.5, UC1.6, UC1.7, UC1.8, UC1.9, UC1.10, UC1.11, UC1.12, UC1.13, UC1.14, CS1.1, CS1.2, CS1.3, CS1.4, CS1.5, NF1.1, NF1.2, NF1.3, NF1.4, NF1.5, NF1.6, NF1.7, NF1.8
Tasks: W28A-83-R2C
Architecture: Compliance quality gates
Tests: QT1.5
"""

from __future__ import annotations

from pathlib import Path

REQUIREMENT_CODE_TRACEABILITY: dict[str, tuple[str, ...]] = {
    "SV1.1": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/server.py",
        "src/file_tools/tools/registry.py",
    ),
    "SV1.2": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/server.py",
        "src/file_tools/tools/registry.py",
    ),
    "SV1.3": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/server.py",
        "src/file_tools/tools/registry.py",
    ),
    "SV1.4": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/server.py",
        "src/file_tools/tools/registry.py",
    ),
    "BO1.1": ("src/file_tools/tools/registry.py", "src/file_mcp_server/main.py"),
    "BO1.2": ("src/file_tools/tools/registry.py", "src/file_mcp_server/main.py"),
    "BO1.3": ("src/file_tools/tools/registry.py", "src/file_mcp_server/main.py"),
    "BO1.4": ("src/file_tools/tools/registry.py", "src/file_mcp_server/main.py"),
    "BO1.5": ("src/file_tools/tools/registry.py", "src/file_mcp_server/main.py"),
    "BR1.1": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "BR1.2": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "BR1.3": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "BR1.4": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "BR1.5": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "BR1.6": (
        "src/file_tools/tools/definitions.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "FR1.1": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "FR1.2": ("src/file_mcp_server/server.py", "src/file_mcp_server/server_runtime.py"),
    "FR1.3": ("src/file_tools/config/adapter.py", "src/file_tools/logging_adapter.py"),
    "FR1.4": (
        "src/file_tools/config/models.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "FR1.5": ("src/file_mcp_server/auth.py",),
    "FR1.6": ("src/file_tools/scope/policy.py",),
    "FR1.7": ("src/file_tools/io/filesystem.py",),
    "FR1.8": ("src/file_tools/io/filesystem.py", "src/file_tools/audit/adapter.py"),
    "FR1.9": ("src/file_tools/search/find.py",),
    "FR1.10": ("src/file_tools/io/__init__.py",),
    "FR1.11": ("src/file_tools/diff/diffgen.py",),
    "FR1.12": ("src/file_tools/diff/meld.py",),
    "FR1.13": (
        "src/file_tools/edit/jsonyaml.py",
        "src/file_tools/edit/xmlhtml.py",
        "src/file_tools/edit/markdown.py",
    ),
    "FR1.14": ("src/file_tools/edit/jsonyaml.py",),
    "FR1.15": ("src/file_tools/edit/xmlhtml.py",),
    "FR1.16": ("src/file_tools/edit/markdown.py",),
    "FR1.17": ("src/file_tools/edit/sedlike.py",),
    "FR1.18": (
        "src/file_tools/validate/policy.py",
        "src/file_tools/validate/validators.py",
    ),
    "FR1.19": ("src/file_tools/audit/logger.py", "src/file_tools/logging_adapter.py"),
    "FR1.20": ("src/file_tools/audit/snapshots.py",),
    "FR1.21": ("src/file_tools/convert/converters.py",),
    "FR1.22": ("src/file_mcp_server/lifecycle.py", "src/file_mcp_server/main.py"),
    "FR1.23": ("src/file_mcp_server/server_runtime.py",),
    "FR1.46": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/auth.py",
    ),
    "FR1.47": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/mcp_api_kit_layer.py",
    ),
    "FR1.24": ("src/file_tools/tools/registry.py",),
    "FR1.25": ("src/file_tools/posix.py",),
    "FR1.26": (
        "src/file_tools/storage/factory.py",
        "src/file_tools/storage/local.py",
        "src/file_tools/storage/s3.py",
        "src/file_tools/storage/webdav.py",
        "src/file_tools/storage/ftp.py",
        "src/file_tools/storage/google_drive.py",
    ),
    "FR1.27": ("src/file_tools/storage/base.py", "src/file_tools/scope/policy.py"),
    "FR1.28": (
        "src/file_tools/storage/s3.py",
        "src/file_tools/storage/webdav.py",
        "src/file_tools/storage/ftp.py",
        "src/file_tools/storage/google_drive.py",
    ),
    "FR1.29": ("src/file_tools/limits.py", "src/file_tools/storage/base.py"),
    "FR1.30": ("src/file_mcp_server/endpoint_health.py",),
    "FR1.31": ("src/file_mcp_server/endpoint_health.py",),
    "FR1.32": (
        "src/file_tools/storage/google_drive.py",
        "src/file_mcp_server/google_drive_admin.py",
    ),
    "FR1.33": (
        "src/file_mcp_server/endpoint_health.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "FR1.34": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/google_drive_admin.py",
    ),
    "FR1.35": ("src/file_tools/storage/webdav.py", "src/file_tools/config/models.py"),
    "FR1.36": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_mcp_server/auth.py",
    ),
    "FR1.37": ("src/file_mcp_server/server_runtime.py",),
    "FR1.38": ("src/file_mcp_server/server_runtime.py",),
    "FR1.39": (
        "src/file_mcp_server/auth.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "FR1.40": ("src/file_mcp_server/server_runtime.py",),
    "FR1.41": ("src/file_mcp_server/server_runtime.py",),
    "FR1.42": ("src/file_tools/tools/definitions.py",),
    "FR1.43": (
        "src/file_mcp_server/server_runtime.py",
        "src/file_tools/audit/logger.py",
    ),
    "FR1.44": ("src/file_mcp_server/server_runtime.py",),
    "FR1.45": ("src/file_mcp_server/server_runtime.py", "src/file_tools/limits.py"),
    "UC1.1": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.2": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.3": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.4": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.5": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.6": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.7": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.8": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.9": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.10": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.11": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.12": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.13": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "UC1.14": (
        "src/file_tools/tools/definitions.py",
        "src/file_tools/tools/registry.py",
        "src/file_mcp_server/server_runtime.py",
    ),
    "CS1.1": ("src/file_mcp_server/auth.py",),
    "CS1.2": ("src/file_tools/scope/policy.py",),
    "CS1.3": ("src/file_tools/config/adapter.py", "src/file_tools/logging_adapter.py"),
    "CS1.4": (
        "src/file_tools/audit/adapter.py",
        "src/file_tools/audit/logger.py",
        "src/file_tools/audit/snapshots.py",
    ),
    "CS1.5": (
        "src/file_tools/limits.py",
        "src/file_tools/search/find.py",
        "src/file_tools/convert/converters.py",
    ),
    "NF1.1": ("src/file_tools/io/filesystem.py", "src/file_tools/audit/adapter.py"),
    "NF1.2": (
        "src/file_tools/limits.py",
        "src/file_tools/search/find.py",
        "src/file_tools/convert/converters.py",
    ),
    "NF1.3": ("src/file_tools/observability.py", "src/file_tools/logging_adapter.py"),
    "NF1.4": (
        "src/file_tools/edit/jsonyaml.py",
        "src/file_tools/edit/sedlike.py",
        "src/file_tools/edit/patch.py",
    ),
    "NF1.5": ("src/file_tools/posix.py",),
    "NF1.6": ("src/file_mcp_server/lifecycle.py", "src/file_mcp_server/main.py"),
    "NF1.7": ("src/file_tools/config/adapter.py", "src/file_tools/config/models.py"),
    "NF1.8": ("src/file_mcp_server/endpoint_health.py",),
}


def mapped_requirement_ids() -> tuple[str, ...]:
    """Return all requirement ids included in the manifest."""
    return tuple(REQUIREMENT_CODE_TRACEABILITY.keys())


def validate_mapped_code_paths(project_root: Path) -> list[str]:
    """Return missing mapped paths relative to project root."""
    missing: list[str] = []
    for paths in REQUIREMENT_CODE_TRACEABILITY.values():
        for rel_path in paths:
            if not (project_root / rel_path).exists():
                missing.append(rel_path)
    return sorted(set(missing))
