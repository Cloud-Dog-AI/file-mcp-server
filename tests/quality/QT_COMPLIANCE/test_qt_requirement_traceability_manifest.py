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

"""QT requirement traceability manifest validation.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Verifies requirement-to-code/test manifest completeness and path validity.
Requirements: SV1.1, SV1.2, SV1.3, SV1.4, BO1.1, BO1.2, BO1.3, BO1.4, BO1.5, BR1.1, BR1.2, BR1.3, BR1.4, BR1.5, BR1.6, FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR1.6, FR1.7, FR1.8, FR1.9, FR1.10, FR1.11, FR1.12, FR1.13, FR1.14, FR1.15, FR1.16, FR1.17, FR1.18, FR1.19, FR1.20, FR1.21, FR1.22, FR1.23, FR1.46, FR1.24, FR1.25, FR1.26, FR1.27, FR1.28, FR1.29, FR1.30, FR1.31, FR1.32, FR1.33, FR1.34, FR1.35, FR1.36, FR1.37, FR1.38, FR1.39, FR1.40, FR1.41, FR1.42, FR1.43, FR1.44, FR1.45, UC1.1, UC1.2, UC1.3, UC1.4, UC1.5, UC1.6, UC1.7, UC1.8, UC1.9, UC1.10, UC1.11, UC1.12, UC1.13, UC1.14, CS1.1, CS1.2, CS1.3, CS1.4, CS1.5, NF1.1, NF1.2, NF1.3, NF1.4, NF1.5, NF1.6, NF1.7, NF1.8
Tasks: W28A-83-R2C
Architecture: Compliance quality gates
Tests: QT1.5
"""


from __future__ import annotations
import pytest

from pathlib import Path

from file_mcp_server.requirement_traceability import (
    REQUIREMENT_CODE_TRACEABILITY,
    validate_mapped_code_paths,
)
from ._helpers import parse_requirements


REQUIREMENT_TEST_TRACEABILITY: dict[str, tuple[str, ...]] = {
    "SV1.1": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "SV1.2": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "SV1.3": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "SV1.4": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BO1.1": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BO1.2": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BO1.3": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BO1.4": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BO1.5": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.1": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.2": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.3": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.4": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.5": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "BR1.6": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.1": ("tests/unit/UT1.24_ToolsRegistry/test_tools_registry.py",),
    "FR1.2": (
        "tests/integration/IT1.23_ServerHttpIntegration/test_server_http_integration.py",
    ),
    "FR1.3": ("tests/unit/UT1.4_ConfigLoader/test_config_loader.py",),
    "FR1.4": (
        "tests/integration/IT1.12_IntegrationMultiProfileRoutingHttp/test_integration_multi_profile_routing_http.py",
    ),
    "FR1.5": ("tests/unit/UT1.3_Auth/test_auth.py",),
    "FR1.6": (
        "tests/integration/IT1.15_IntegrationScopedOps/test_integration_scoped_ops.py",
    ),
    "FR1.7": ("tests/unit/UT1.10_Filesystem/test_filesystem.py",),
    "FR1.8": ("tests/unit/UT1.10_Filesystem/test_filesystem.py",),
    "FR1.9": ("tests/unit/UT1.19_Search/test_search.py",),
    "FR1.10": (
        "tests/integration/IT1.3_IntegrationBase64FileOps/test_integration_base64_file_ops.py",
    ),
    "FR1.11": (
        "tests/integration/IT1.5_IntegrationDiffFilesHttp/test_integration_diff_files_http.py",
    ),
    "FR1.12": (
        "tests/integration/IT1.11_IntegrationMeldOptionalityHttp/test_integration_meld_optionality_http.py",
    ),
    "FR1.13": (
        "tests/integration/IT1.21_IntegrationStructuredFormats/test_integration_structured_formats.py",
    ),
    "FR1.14": (
        "tests/integration/IT1.9_IntegrationJsonYamlGetMergeHttp/test_integration_json_yaml_get_merge_http.py",
    ),
    "FR1.15": (
        "tests/integration/IT1.21_IntegrationStructuredFormats/test_integration_structured_formats.py",
    ),
    "FR1.16": (
        "tests/integration/IT1.10_IntegrationMarkdownAdvancedHttp/test_integration_markdown_advanced_http.py",
    ),
    "FR1.17": (
        "tests/integration/IT1.18_IntegrationSedlikeTransactionHttp/test_integration_sedlike_transaction_http.py",
    ),
    "FR1.18": ("tests/unit/UT1.25_Validate/test_validate.py",),
    "FR1.19": (
        "tests/system/ST1.1_SystemAuditIntegrity/test_system_audit_integrity.py",
    ),
    "FR1.20": (
        "tests/system/ST1.13_SystemSnapshotRetention/test_system_snapshot_retention.py",
        "tests/integration/IT1.20_IntegrationStructuredAuditSnapshot/test_integration_structured_audit_snapshot.py",
    ),
    "FR1.21": ("tests/unit/UT1.5_Convert/test_convert.py",),
    "FR1.22": ("tests/unit/UT1.15_Lifecycle/test_lifecycle.py",),
    "FR1.23": (
        "tests/integration/IT1.23_ServerHttpIntegration/test_server_http_integration.py",
    ),
    "FR1.46": (
        "tests/integration/IT1.25_IntegrationA2AAuthContract/test_integration_a2a_auth_contract.py",
    ),
    "FR1.47": (
        "tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py",
        "tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py",
    ),
    "FR1.24": ("tests/unit/UT1.23_ToolReuse/test_tool_reuse.py",),
    "FR1.25": ("tests/unit/UT1.17_Posix/test_posix.py",),
    "FR1.26": (
        "tests/integration/IT1.14_IntegrationRemoteStorageBackendsHttp/test_integration_remote_storage_backends_http.py",
    ),
    "FR1.27": (
        "tests/integration/IT1.13_IntegrationRemoteBackendToolMatrixHttp/test_integration_remote_backend_tool_matrix_http.py",
    ),
    "FR1.28": (
        "tests/integration/IT1.13_IntegrationRemoteBackendToolMatrixHttp/test_integration_remote_backend_tool_matrix_http.py",
    ),
    "FR1.29": (
        "tests/integration/IT1.13_IntegrationRemoteBackendToolMatrixHttp/test_integration_remote_backend_tool_matrix_http.py",
    ),
    "FR1.30": (
        "tests/system/ST1.7_SystemEndpointRestartThreshold/test_system_endpoint_restart_threshold.py",
        "tests/unit/UT1.9_EndpointHealth/test_endpoint_health.py",
    ),
    "FR1.31": (
        "tests/system/ST1.7_SystemEndpointRestartThreshold/test_system_endpoint_restart_threshold.py",
        "tests/unit/UT1.9_EndpointHealth/test_endpoint_health.py",
    ),
    "FR1.32": (
        "tests/unit/UT1.11_GoogleDriveAdmin/test_google_drive_admin.py",
        "tests/unit/UT1.12_GoogleDriveOauthHelper/test_google_drive_oauth_helper.py",
        "tests/unit/UT1.13_GoogleDriveSetupScript/test_google_drive_setup_script.py",
        "tests/integration/IT1.7_IntegrationGoogleDriveLiveHttp/test_integration_google_drive_live_http.py",
    ),
    "FR1.33": (
        "tests/system/ST1.7_SystemEndpointRestartThreshold/test_system_endpoint_restart_threshold.py",
        "tests/unit/UT1.9_EndpointHealth/test_endpoint_health.py",
    ),
    "FR1.34": (
        "tests/unit/UT1.22_ServerRuntime/test_server_runtime.py",
        "tests/unit/UT1.11_GoogleDriveAdmin/test_google_drive_admin.py",
    ),
    "FR1.35": ("tests/unit/UT1.26_WebdavStorage/test_webdav_storage.py",),
    "FR1.36": (
        "tests/integration/IT1.12_IntegrationMultiProfileRoutingHttp/test_integration_multi_profile_routing_http.py",
    ),
    "FR1.37": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.38": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.39": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.40": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.41": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.42": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.43": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.44": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "FR1.45": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.1": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.2": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.3": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.4": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.5": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.6": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.7": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.8": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.9": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.10": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.11": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.12": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.13": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "UC1.14": ("tests/quality/QT_COMPLIANCE/test_qt_traceability.py",),
    "CS1.1": (
        "tests/unit/UT1.3_Auth/test_auth.py",
        "tests/application/AT1.9_ApplicationSecurityBoundary/test_application_security_boundary.py",
    ),
    "CS1.2": (
        "tests/unit/UT1.3_Auth/test_auth.py",
        "tests/application/AT1.9_ApplicationSecurityBoundary/test_application_security_boundary.py",
    ),
    "CS1.3": (
        "tests/unit/UT1.3_Auth/test_auth.py",
        "tests/application/AT1.9_ApplicationSecurityBoundary/test_application_security_boundary.py",
    ),
    "CS1.4": (
        "tests/system/ST1.1_SystemAuditIntegrity/test_system_audit_integrity.py",
        "tests/integration/IT1.20_IntegrationStructuredAuditSnapshot/test_integration_structured_audit_snapshot.py",
    ),
    "CS1.5": (
        "tests/unit/UT1.3_Auth/test_auth.py",
        "tests/application/AT1.9_ApplicationSecurityBoundary/test_application_security_boundary.py",
    ),
    "NF1.1": ("tests/unit/UT1.10_Filesystem/test_filesystem.py",),
    "NF1.2": ("tests/unit/UT1.19_Search/test_search.py",),
    "NF1.3": ("tests/unit/UT1.16_Observability/test_observability.py",),
    "NF1.4": (
        "tests/unit/UT1.7_EditStructured/test_edit_structured.py",
        "tests/integration/IT1.19_IntegrationStoryMultitypeCrudHttp/test_integration_story_multitype_crud_http.py",
    ),
    "NF1.5": ("tests/unit/UT1.17_Posix/test_posix.py",),
    "NF1.6": ("tests/unit/UT1.15_Lifecycle/test_lifecycle.py",),
    "NF1.7": ("tests/unit/UT1.4_ConfigLoader/test_config_loader.py",),
    "NF1.8": ("tests/unit/UT1.9_EndpointHealth/test_endpoint_health.py",),
}
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_manifest_covers_all_requirements(project_root: Path) -> None:
    requirements = parse_requirements(project_root / "docs/REQUIREMENTS.md")
    req_ids = {req.req_id for req in requirements}
    missing_code_map = sorted(req_ids - set(REQUIREMENT_CODE_TRACEABILITY.keys()))
    missing_test_map = sorted(req_ids - set(REQUIREMENT_TEST_TRACEABILITY.keys()))
    assert not missing_code_map, "Missing code-map requirement ids:\n- " + "\n- ".join(
        missing_code_map
    )
    assert not missing_test_map, "Missing test-map requirement ids:\n- " + "\n- ".join(
        missing_test_map
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_manifest_mapped_paths_exist(project_root: Path) -> None:
    missing_code_paths = validate_mapped_code_paths(project_root)
    assert not missing_code_paths, "Mapped code paths missing:\n- " + "\n- ".join(
        missing_code_paths
    )

    missing_test_paths: list[str] = []
    for paths in REQUIREMENT_TEST_TRACEABILITY.values():
        for rel_path in paths:
            if not (project_root / rel_path).exists():
                missing_test_paths.append(rel_path)
    missing_test_paths = sorted(set(missing_test_paths))
    assert not missing_test_paths, "Mapped test paths missing:\n- " + "\n- ".join(
        missing_test_paths
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_manifest_entries_not_empty() -> None:
    empty_code = sorted(
        req for req, paths in REQUIREMENT_CODE_TRACEABILITY.items() if not paths
    )
    empty_test = sorted(
        req for req, paths in REQUIREMENT_TEST_TRACEABILITY.items() if not paths
    )
    assert not empty_code, "Empty code mapping entries:\n- " + "\n- ".join(empty_code)
    assert not empty_test, "Empty test mapping entries:\n- " + "\n- ".join(empty_test)
