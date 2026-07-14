---
template-id: T-TST
template-version: 1.1
applies-to: docs/TESTS.md
project: file-mcp-server
doc-last-updated: 2026-06-23T14:02:08Z
doc-git-commit: 157f34c69faf321586cdb0ec962c0f4a9d1a3f1b
doc-git-branch: main
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-23T14:02:08Z
req-trace-version: 1.0
total-tests: 388
coverage-percent: 100
---

# Tests

## Service Scope
Deterministic file operations, structured edits, conversion, validation, and storage-backend actions exposed through profile-governed HTTP and MCP surfaces.

## Test Inventory
| Tier | Present | Notes |
|------|---------|-------|
| `quality` | Yes | Repository contains the `quality` test tier. |
| `unit` | Yes | Repository contains the `unit` test tier. |
| `system` | Yes | Repository contains the `system` test tier. |
| `integration` | Yes | Repository contains the `integration` test tier. |
| `application` | Yes | Repository contains the `application` test tier. |
| `private` | Yes | Repository contains the `private` test tier. |

## Current Evidence Model
- The repository keeps execution evidence in repo-local working reports and rerunnable pytest suites.
- Before release, rerun the relevant `QT`, `UT`, `ST`, `IT`, and `AT` tiers against the intended environment overlays.
- This document records the current catalogue rather than claiming a release verdict.

## W28E-1802C Stream-C Validation Snapshot
- Date: `2026-06-24`
- Local WebUI browser pack: `apps/file-mcp` Playwright `tests/smoke/all-pages.spec.ts`, `tests/e2e/routes.spec.ts`, `tests/a11y.spec.ts` via Vite/local backend -> `15 passed`.
- Local Docker Stream-C proof: `tests/e2e/stream-c-proof.spec.ts` against image `sha256:0fe829ff00c043d98a27b344de72b78d14ae6c0ae55e61345734151907211719` -> `2 passed`.
- Preprod Stream-C browser proof: `tests/e2e/stream-c-proof.spec.ts` against `https://filemcpserver0.cloud-dog.net` -> `2 passed`; 18 canonical screenshot rows and 12 alias rows all PASS.
- Preprod smoke/routes/a11y pack: `tests/smoke/all-pages.spec.ts`, `tests/e2e/routes.spec.ts`, `tests/a11y.spec.ts` -> `19 passed`, including 16 axe WCAG2AA page checks.
- Sibling browser smoke: target plus `chatclient0`, `expertagent0`, `notificationagent0`, and `filemcpserver0` sentinel -> all PASS in real Chromium.
- Deployed image identity: image id `sha256:8d291fcedf7eb2710e8fe3d7e87935b82442a0f9ba1d08d5a660ee5c9b9c8032`; registry digest `sha256:c5d1fca676fa0497507b2c9a007550c4c613d2c77694380b18951c7b1a6cee68`.
- Evidence: `cloud-dog-ai-platform-standards/working/evidence/W28E-1802C/current/`.

## W28A-961 Validation Snapshot
- Date: `2026-04-16`
- Unit: `.venv/bin/python -m pytest tests/unit --env tests/env-UT -q` → `177 passed in 22.19s`
- Integration: `.venv/bin/python -m pytest tests/integration --env tests/env-IT -q` → `37 passed, 10 skipped in 136.52s`
- Application: `.venv/bin/python -m pytest tests/application --env tests/env-AT -q --timeout=600` → `25 passed, 1 skipped in 148.16s`
- Monorepo Playwright app suite: `cloud-dog-ai-ui-monorepo/apps/file-mcp npm run e2e` with `E2E_USE_LOCAL_SERVER=0 E2E_BASE_URL=http://127.0.0.1:5186` → `47 passed (2.1m)`
- Registry push: `docker push <internal-registry>:443/cloud-dog/file-mcp-server:latest` → `sha256:27c97601f7b2ee602e59f2a6b203478b2aa556444b6333d16ef188ba6b4ca6f5`
- PC28 bespoke grep evidence:
  - `grep -RInE 'os\.(getenv|environ)' src/file_mcp_server/main.py` → `0 matches: main.py direct env access`
  - `grep -RInE '^import logging$|logging\.(getLogger|basicConfig)\(' src/file_mcp_server/mcp_tool_audit_shim.py` → `0 matches: mcp_tool_audit_shim raw logging`
  - `grep -RInE '^import logging$|logging\.(getLogger|basicConfig)\(' src/file_mcp_server` → `0 matches: file_mcp_server raw logging`
- Cleanup: `./server_control.sh --env tests/env-ST stop all` followed by `rm -f database/*.db` → no listeners on `8060-8063` and no remaining `database/*.db`
- Local Docker build: `./docker-build.sh test` → `Build OK: cloud-dog/file-mcp-server:test`
- Preprod probes:
  - `curl -sS -D - https://filemcpserver0.example.com/health` → `HTTP/1.1 200 OK`
  - `curl -sS -D - https://filemcpserver0.example.com/status` → `HTTP/1.1 200 OK`

## Standard Commands
```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
.venv/bin/python -m pytest tests/system --env tests/env-ST -q
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q
.venv/bin/python -m pytest tests/application --env tests/env-AT -q --timeout=600
```

## Notes
- Top-level test directories present: `__pycache__`, `application`, `integration`, `private`, `quality`, `system`, `unit`.
- Environment overlays and private credentials are intentionally not published in this document set.

## W28A-510 Traceability Addendum
| Test ID | Requirement | File | Coverage |
|---|---|---|---|
| `ST1.18` | `FR1.9` | `tests/test_st_time_based_search.py` | Verifies `modified_after`/`modified_before` filters return and exclude the uploaded file as expected, with cleanup. |


## Test File References
The following test filenames are present in the repository and are included for QT traceability file-reference checks.

- `test_admin_identity.py`
- `test_api_kit_contract.py`
- `test_application_a2a_auth_workflow.py`
- `test_application_compound_release_workflow.py`
- `test_application_conversion_edit_workflow.py`
- `test_application_conversion_structured_workflow.py`
- `test_application_lifecycle_workflow.py`
- `test_application_multifile_transaction_workflow.py`
- `test_application_preprod_profile_chain_http.py`
- `test_application_safe_edit_workflow.py`
- `test_application_search_edit_audit_workflow.py`
- `test_application_security_boundary.py`
- `test_application_webui_admin.py`
- `test_audit.py`
- `test_audit_log_format.py`
- `test_auth.py`
- `test_auth_status_probe.py`
- `test_config_loader.py`
- `test_flat_role_login.py`
- `test_w28c_1702_fm6_anon_gate.py`
- `test_w28c_1702_forensic_fixes.py`
- `test_convert.py`
- `test_database_abstraction.py`
- `test_database_migration.py`
- `test_database_migration_multibackend.py`
- `test_diff.py`
- `test_docker_container_remote_storage_backends.py`
- `test_docker_container_runtime.py`
- `test_dynamic_profile_crud_lifecycle.py`
- `test_edit_structured.py`
- `test_encoding.py`
- `test_endpoint_health.py`
- `test_filesystem.py`
- `test_google_drive_admin.py`
- `test_google_drive_oauth_helper.py`
- `test_google_drive_oauth_live.py`
- `test_google_drive_setup_script.py`
- `test_google_drive_storage.py`
- `test_integration_a2a_auth_contract.py`
- `test_integration_base64_file_ops.py`
- `test_integration_config_crud_identity_workflow.py`
- `test_integration_config_matrix_harness_http.py`
- `test_integration_diff_files_http.py`
- `test_integration_filesystem_path_tools_http.py`
- `test_integration_google_drive_live_http.py`
- `test_integration_iterative_cycle_guard_http.py`
- `test_integration_jobs_managed_file_ops.py`
- `test_integration_json_yaml_get_merge_http.py`
- `test_integration_markdown_advanced_http.py`
- `test_integration_meld_optionality_http.py`
- `test_integration_multi_profile_routing_http.py`
- `test_integration_remote_backend_tool_matrix_http.py`
- `test_integration_remote_storage_backends_http.py`
- `test_integration_scoped_ops.py`
- `test_integration_search_http.py`
- `test_integration_sedlike_file_http.py`
- `test_integration_sedlike_transaction_http.py`
- `test_integration_story_multitype_crud_http.py`
- `test_integration_structured_audit_snapshot.py`
- `test_integration_structured_formats.py`
- `test_integration_yaml_file_structured_ops.py`
- `test_integrity_running.py`
- `test_jobs_runtime.py`
- `test_lifecycle.py`
- `test_lifecycle_simulation.py`
- `test_logging_compliance.py`
- `test_observability.py`
- `test_package_compliance.py`
- `test_param_alias_fallback.py`
- `test_posix.py`
- `test_profile_crud.py`
- `test_profile_lifecycle.py`
- `test_qt1_security_suite.py`
- `test_qt26_secrets_separation.py`
- `test_qt27_bespoke_code_scan.py`
- `test_qt3_documentation_suite.py`
- `test_qt_migration_completeness.py`
- `test_qt_package_adoption.py`
- `test_qt_requirement_traceability_manifest.py`
- `test_qt_rules_compliance.py`
- `test_qt_traceability.py`
- `test_qt_vault_config_contract.py`
- `test_remote_env_helpers.py`
- `test_remote_storage_placeholder_validation.py`
- `test_rotation_config.py`
- `test_scope_policy.py`
- `test_search.py`
- `test_sedlike.py`
- `test_server_dispatch.py`
- `test_server_http_integration.py`
- `test_server_runtime.py`
- `tests/smoke/SM1.2_NoUnguardedRoute/test_no_unguarded_route_meta.py`
- `test_st_time_based_search.py`
- `test_system_audit_integrity.py`
- `test_system_auth_health.py`
- `test_system_conversion_backend_selection.py`
- `test_system_conversion_matrix.py`
- `test_system_conversion_optionality.py`
- `test_system_conversion_real_backends.py`
- `test_system_dry_run_contract.py`
- `test_system_endpoint_restart_threshold.py`
- `test_system_error_contract.py`
- `test_system_limits.py`
- `test_system_limits_timeout.py`
- `test_system_read_partial_ranges.py`
- `test_system_sed_transaction_contract.py`
- `test_system_snapshot_retention.py`
- `test_system_structured_path_edge_cases.py`
- `test_system_structured_rollback_contract.py`
- `test_system_validate_file_tool.py`
- `test_tool_reuse.py`
- `test_tools_registry.py`
- `test_validate.py`
- `test_webdav_storage.py`
- `test_webui_end_to_end.py`

## Traceability Matrix

| Requirement | Test File | Test Function/Class | Status |
|---|---|---|---|
| FR1.1 (Tool Boundary & Schema) | `tests/unit/UT1.24_ToolsRegistry/test_tools_registry.py` | UT1.24 suite | COVERED |
| FR1.1 (Tool Boundary & Schema) | `tests/unit/UT1.36_ParamAliasFallback/test_param_alias_fallback.py` | UT1.36 suite (alias-source/param collisions; preserves `b64_decode_to_file` `data`) | COVERED |
| FR1.1 (Tool Boundary & Schema) | `tests/integration/IT1.3_IntegrationBase64FileOps/test_integration_base64_file_ops.py` | `test_base64_file_roundtrip_over_http` | COVERED |
| FR1.3 (Config Precedence) | `tests/unit/UT1.4_ConfigLoader/test_config_loader.py` | `test_load_config_env_precedence`, `test_load_config_os_environ_precedence`, `test_load_config_defaults_only`, `test_load_config_env_override_precedence` | COVERED |
| FR1.5 (Authentication) | `tests/unit/UT1.3_Auth/test_auth.py` | `test_auth_accepts_valid_key`, `test_auth_rejects_invalid_key`, `test_auth_rejects_missing_token`, `test_multi_profile_verifier_query_profile_and_key_routing` | COVERED |
| FR1.6 (Scope Enforcement) | `tests/unit/UT1.18_ScopePolicy/test_scope_policy.py` | `test_scope_denies_outside_root`, `test_scope_denies_glob`, `test_scope_allows_glob`, `test_scope_denies_extension`, `test_scope_denies_read_only_on_write` | COVERED |
| FR1.7 (File Read Operations) | `tests/unit/UT1.10_Filesystem/test_filesystem.py` | `test_atomic_write_and_read`, `test_list_dir` | COVERED |
| FR1.8 (File Mutation Operations) | `tests/unit/UT1.10_Filesystem/test_filesystem.py` | `test_atomic_write_respects_overwrite`, `test_write_text_and_copy_move`, `test_delete_file_missing_ok` | COVERED |
| FR1.8 (Dry Run) | `tests/system/ST1.6_SystemDryRunContract/test_system_dry_run_contract.py` | `test_dry_run_mutations_do_not_change_files_and_are_audited` | COVERED |
| FR1.9 (Search) | `tests/unit/UT1.19_Search/test_search.py` | `test_search_paths`, `test_search_paths_glob`, `test_search_content`, `test_search_content_regex`, `test_search_content_max_results` | COVERED |
| FR1.9 (Search) | `tests/integration/IT1.16_IntegrationSearchHttp/test_integration_search_http.py` | IT1.16 suite | COVERED |
| FR1.9 (Time-based Search) | `tests/test_st_time_based_search.py` | time-based search system suite | COVERED |
| FR1.11 (Diff Generation) | `tests/unit/UT1.6_Diff/test_diff.py` | `test_diff_text_contains_changes`, `test_diff_files` | COVERED |
| FR1.12 (Meld Integration) | `tests/unit/UT1.6_Diff/test_diff.py` | `test_meld_available_returns_bool`, `test_meld_unavailable_returns_warning` | COVERED |
| FR1.13 (Structured Edits General) | `tests/unit/UT1.7_EditStructured/test_edit_structured.py` | `test_json_yaml_crud`, `test_xml_html_edits`, `test_markdown_section_edits` | COVERED |
| FR1.14 (Structured Edits JSON/YAML) | `tests/unit/UT1.7_EditStructured/test_edit_structured.py` | `test_json_yaml_crud`, `test_json_yaml_move_copy_merge_matrix` | COVERED |
| FR1.14 (Structured Edits JSON/YAML) | `tests/integration/IT1.9_IntegrationJsonYamlGetMergeHttp/test_integration_json_yaml_get_merge_http.py` | IT1.9 suite | COVERED |
| FR1.15 (Structured Edits XML/HTML) | `tests/unit/UT1.7_EditStructured/test_edit_structured.py` | `test_xml_html_edits` | COVERED |
| FR1.16 (Structured Edits Markdown) | `tests/unit/UT1.7_EditStructured/test_edit_structured.py` | `test_markdown_section_edits` | COVERED |
| FR1.16 (Structured Edits Markdown) | `tests/integration/IT1.10_IntegrationMarkdownAdvancedHttp/test_integration_markdown_advanced_http.py` | IT1.10 suite | COVERED |
| FR1.17 (Sed-like Edits) | `tests/unit/UT1.20_Sedlike/test_sedlike.py` | `test_replace_regex`, `test_insert_before_after_line`, `test_delete_matching_lines`, `test_replace_line_range`, `test_apply_edits_atomic_on_error`, `test_apply_edits_success` | COVERED |
| FR1.17 (Sed-like Edits) | `tests/integration/IT1.17_IntegrationSedlikeFileHttp/test_integration_sedlike_file_http.py` | IT1.17 suite | COVERED |
| FR1.18 (Validation) | `tests/unit/UT1.25_Validate/test_validate.py` | `test_validate_json`, `test_validate_yaml`, `test_validate_xml`, `test_validate_html`, `test_validate_markdown`, `test_validation_strict_mode`, `test_validation_warn_mode`, `test_validation_ignore_mode` | COVERED |
| FR1.18 (Validation) | `tests/system/ST1.16_SystemValidateFileTool/test_system_validate_file_tool.py` | ST1.16 suite | COVERED |
| FR1.19 (Audit Logging) | `tests/unit/UT1.2_Audit/test_audit.py` | `test_build_event`, `test_audit_logger_writes`, `test_audit_logger_uses_explicit_actor_identity` | COVERED |
| FR1.19 (Audit Logging) | `tests/system/ST1.1_SystemAuditIntegrity/test_system_audit_integrity.py` | `test_audit_log_integrity_append_only` | COVERED |
| FR1.20 (Snapshots) | `tests/unit/UT1.2_Audit/test_audit.py` | `test_create_snapshot` | COVERED |
| FR1.20 (Snapshots) | `tests/system/ST1.13_SystemSnapshotRetention/test_system_snapshot_retention.py` | `test_snapshot_retention_prunes_old_snapshot_dirs` | COVERED |
| FR1.21 (Conversion Pipeline) | `tests/unit/UT1.5_Convert/test_convert.py` | `test_convert_file_with_dummy_backend`, `test_convert_file_no_backend`, `test_convert_file_max_input_mb`, `test_convert_file_timeout` | COVERED |
| FR1.21 (Conversion Pipeline) | `tests/system/ST1.3_SystemConversionMatrix/test_system_conversion_matrix.py` | ST1.3 suite | COVERED |
| FR1.24 (Tool Reuse Outside Server) | `tests/unit/UT1.23_ToolReuse/test_tool_reuse.py` | `test_file_tools_helpers_reusable` | COVERED |
| FR1.25 (POSIX Compliance) | `tests/unit/UT1.17_Posix/test_posix.py` | UT1.17 suite | COVERED |
| FR1.26 (Remote Storage Backends) | `tests/integration/IT1.14_IntegrationRemoteStorageBackendsHttp/test_integration_remote_storage_backends_http.py` | IT1.14 suite | COVERED |
| FR1.30 (Endpoint Health Startup) | `tests/unit/UT1.9_EndpointHealth/test_endpoint_health.py` | `test_run_startup_checks_marks_local_healthy`, `test_classify_http_error_503_as_busy_temporary`, `test_recover_backend_after_failure` | COVERED |
| FR1.33 (Restart Threshold) | `tests/system/ST1.7_SystemEndpointRestartThreshold/test_system_endpoint_restart_threshold.py` | ST1.7 suite | COVERED |
| FR1.36 (Multi-Profile Routing) | `tests/integration/IT1.12_IntegrationMultiProfileRoutingHttp/test_integration_multi_profile_routing_http.py` | `test_multi_profile_selection_auth_and_scope_controls` | COVERED |
| FR1.46 (A2A Health Auth) | `tests/integration/IT1.25_IntegrationA2AAuthContract/test_integration_a2a_auth_contract.py` | `test_a2a_health_auth_matrix_200_200_200` | COVERED |
| R-DB-01 (DB access abstraction) | `tests/unit/UT1.29_DatabaseAbstraction/test_database_abstraction.py` | `test_ut_db_01_engine_factory_creates_sqlite_engine` | COVERED |
| R-DB-03 (Session management) | `tests/unit/UT1.29_DatabaseAbstraction/test_database_abstraction.py` | `test_ut_db_02_session_manager_roundtrip` | COVERED |
| R-DB-06 (DB readiness probe) | `tests/unit/UT1.29_DatabaseAbstraction/test_database_abstraction.py` | `test_ut_db_03_probe_database_reports_healthy` | COVERED |
| R-DB-08 / NF1.7 (Multi-dialect versioning) | `tests/system/ST1.17_SystemDatabaseMigration/test_database_migration_multibackend.py` | ST1.17 suite | COVERED |
| CFG-01..CFG-04 (Profile CRUD) | `tests/application/AT_ProfileCRUD/test_profile_crud.py` | AT_ProfileCRUD suite | COVERED |
| CFG-01..CFG-04 / FR1.47 (Dynamic Profile CRUD) | `tests/application/AT1.11_DynamicProfileCRUDLifecycle/test_dynamic_profile_crud_lifecycle.py` | AT1.11 suite | COVERED |
| CFG-08..CFG-11 / FR1.47 (User/Group/Key mgmt) | `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | `test_it1_26_user_key_profile_lifecycle_supports_mcp_file_operations` | COVERED |
| CFG-13 (Admin-only CRUD) | `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | (admin gating verified in lifecycle workflow) | COVERED |
| FR1.37 (Web UI Routes) | `tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py` | AT_WEBUI suite | COVERED |
| FR1.44 (Web UI Accessibility) | `tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py` | AT1.13 suite | COVERED |
| FR1.47 (Web UI Standards Merge) | `tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py` + `tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py` | WebUI end-to-end and admin WebUI suites | COVERED |
| CFG-06 (A2A broadcast) | `tests/unit/UT_CFG06_A2AEvents/test_config_change_events.py` + `tests/integration/IT_CFG06_A2AEvents/test_a2a_events_integration.py` | UT_CFG06_A2AEvents + IT_CFG06_A2AEvents | IMPLEMENTED |
| CFG-12 (Audit logging for CRUD) | `tests/unit/UT1.2_Audit/test_audit.py` + `tests/unit/UT_AuditLogFormat/test_audit_log_format.py` + `tests/integration/IT1.20_IntegrationStructuredAuditSnapshot/test_integration_structured_audit_snapshot.py` + `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | `test_audit_logger_writes`, `test_audit_logger_uses_explicit_actor_identity`, `test_audit_event_has_all_au3_fields`, `test_structured_edit_with_audit_and_snapshot`, `test_it1_26_user_key_profile_lifecycle_supports_mcp_file_operations` (platform capability via `cloud_dog_logging.AuditLogger.log_crud`, wrapped by `file_tools.audit.adapter.AuditLogger`) | IMPLEMENTED |
| FR1.32 (Google Drive OAuth Folder Binding) | `tests/application/AT1.12_GoogleDriveOauthLive/test_google_drive_oauth_live.py` | AT1.12 suite | COVERED |

## 2. Coverage map

Mandatory 10-column schema per PS-REQ-TEST-TRACE v1.0 §4.2. Every test module binds to its semantic
`@pytest.mark.req(...)` requirement(s); the W28C-1711-R3 `@pytest.mark.probe` placeholders were
**retired and rebound** to capability requirements (`FR-001`..`FR-029`, `CS-001`..`CS-016`,
`NF-001`..`NF-005`) in W28E-1802A — `grep -rn "@pytest.mark.probe" tests/` returns zero matches.
`Last run commit` is `design-bound (run: Stream-B/C)` because Stream-A binds and designs; execution
verdicts are produced by Stream-B (UT/IT/AT/ST/QT) and Stream-C (WebUI/E2E). Rows are keyed by test
module; a module may contain several `def test_*` functions sharing the module's bindings
(388 test functions across 117 modules).

| Test ID | Tier | Use case | Requirement | Surface | Scenario | Variants | Env files | Known issue | Last run commit |
|---|---|---|---|---|---|---|---|---|---|
| `UT1.24_ToolsRegistry` | UT | UC-001 | `FR-001` | `mcp` | ToolBoundarySchemaContract | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.36_ParamAliasFallback` | UT | UC-001 | `FR-001` | `mcp` | ParamAliasFallback | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `IT1.3_IntegrationBase64FileOps` | IT | UC-002 | `FR-002` | `mcp` | Base64FileRoundtrip | — | tests/env-IT | — | design-bound (run: Stream-B) |
| `UT1.6_Diff` | UT | UC-005 | `FR-003` | `mcp` | UnifiedDiffPreview | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.7_EditStructured` | UT | UC-003 | `FR-004` | `mcp` | StructuredCRUD | json/yaml/xml/html/md | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.20_Sedlike` | UT | UC-003 | `FR-005` | `mcp` | SedTransaction | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.25_Validate` | UT | UC-003 | `FR-006` | `mcp` | ValidationPolicy | strict/warn/ignore | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.1_ApiKitContract` | UT | UC-001 | `FR-007` | `api` | ApiKitTransportContract | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.5_Convert` | UT | UC-004 | `FR-008` | `mcp` | ConversionPipeline | pdf/docx/xlsx | tests/env-UT | — | design-bound (run: Stream-B) |
| `ST1.2_SystemAuthHealth` | ST | UC-010 | `FR-009` | `api` | HealthReadinessLive | — | tests/env-ST | — | design-bound (run: Stream-B) |
| `UT1.23_ToolReuse` | UT | UC-002 | `FR-010` | `internal` | LibraryFirstReuse | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.17_Posix` | UT | UC-001 | `FR-011` | `internal` | PosixCompliance | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `IT1.14_RemoteStorageBackendsHttp` | IT | UC-008 | `FR-012` | `mcp` | RemoteBackendMatrix | local/s3/webdav/ftp/gdrive | tests/env-IT | — | design-bound (run: Stream-B) |
| `UT1.4_ConfigLoader` | UT | UC-002 | `FR-013` | `internal` | ConfigPrecedence | env/file/yaml/defaults | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.9_EndpointHealth` | UT | UC-010 | `FR-014`, `FR-020` | `internal` | EndpointHealthClassifyRecover | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `AT1.12_GoogleDriveOauthLive` | AT | UC-011 | `FR-015` | `api` | GoogleDriveOAuthBinding | — | tests/env-AT | — | design-bound (run: Stream-B) |
| `IT1.12_IntegrationMultiProfileRoutingHttp` | IT | UC-014 | `FR-016` | `api` | MultiProfileRouting | query/header | tests/env-IT | — | design-bound (run: Stream-B) |
| `UT1.3_Auth` | UT | UC-001 | `FR-017` | `api` | ApiKeyProfileAwareAuth | X-API-Key/bearer/matching/conflicting | tests/env-UT | — | W28R-3008 |
| `IT1.25_IntegrationA2AAuthContract` | IT | UC-001 | `FR-017` | `a2a` | A2AHealthAuthContract | anon/invalid/X-API-Key/bearer | tests/env-IT | — | W28R-3008 |
| `UT1.10_Filesystem` | UT | UC-001 | `FR-018` | `mcp` | FileReadWriteAtomic | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `ST1.11_SystemReadPartialRanges` | ST | UC-001 | `FR-018` | `mcp` | PartialRangeRead | byte/line | tests/env-ST | — | design-bound (run: Stream-B) |
| `IT1.16_IntegrationSearchHttp` | IT | UC-003 | `FR-019` | `mcp` | Search | glob/regex/content | tests/env-IT | — | design-bound (run: Stream-B) |
| `UT1.14_GoogleDriveStorage` | UT | UC-011 | `FR-021` | `internal` | GoogleDriveBackendSemantics | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `UT1.16_Observability` | UT | UC-006 | `FR-022` | `internal` | OperationalLogging | — | tests/env-UT | — | design-bound (run: Stream-B) |
| `IT1_30_AuthStatusProbe` | IT | UC-001 | `FR-023` | `api` | AuthStatusProbe | — | tests/env-IT | — | design-bound (run: Stream-B) |
| `UT1.35_FlatRoleLogin` | UT | UC-022 | `FR-024`, `CS-001`, `CS-005`, `CS-009`, `CS-013` | `api` | AnonAndRoleGate | anon/read-only/missing | tests/env-UT | — | design-bound (run: Stream-B) |
| `ST1.18_TimeBasedSearch` | ST | UC-003 | `FR-025` | `mcp` | TimeBasedSearchWindow | modified_after/before | tests/env-ST | — | design-bound (run: Stream-B) |
| `tests/unit/** (cluster)` | UT | UC-001 | `FR-026` | `api` | UnitTierCorrectness | whole unit dir | tests/env-UT | — | design-bound (run: Stream-B) |
| `tests/application/** (cluster)` | AT | UC-002 | `FR-027` | `a2a` | ApplicationWorkflows | whole application dir | tests/env-AT | — | design-bound (run: Stream-B) |
| `tests/system/** (cluster)` | ST | UC-006 | `FR-028` | `internal` | SystemContracts | whole system dir | tests/env-ST | — | design-bound (run: Stream-B) |
| `tests/integration/** (cluster)` | IT | UC-008 | `FR-029` | `mcp` | IntegrationFlows | whole integration dir | tests/env-IT | — | design-bound (run: Stream-B) |
| `AT_ProfileCRUD` | AT | UC-015 | `FR-016` | `api` | ProfileCRUD | C/R/U/D | tests/env-AT | — | design-bound (run: Stream-B) |
| `IT1.26_IntegrationConfigCrudIdentityWorkflow` | IT | UC-017 | `FR-016` | `api` | IdentityCRUDWorkflow | user/group/key | tests/env-IT | — | design-bound (run: Stream-B) |
| `tests/unit/UT1.36_CookieSessionIsolation/test_cookie_session_isolation.py` | UT | UC-001 | `FR-024`, `CS-001` | `webui` | CookieSessionIsolation | session/anon | tests/env-UT | — | run: WS-A |
| `tests/unit/UT1.37_RestFileLifecycle/test_rest_file_lifecycle_helpers.py` | UT | UC-001 | `FR-012`, `FR-017`, `CS-002` | `api` | RestFileLifecycleHelpers | upload/list/download | tests/env-UT | — | run: WS-A |
| `tests/unit/UT1.38_McpRoleGuards/test_mcp_role_guards.py` | UT | UC-001 | `CS-010` | `mcp` | McpRoleGuards | read-write/read-only | tests/env-UT | — | run: WS-A |
| `tests/unit/UT1.39_W28E1846WebUiAliases/test_webui_aliases.py` | UT | UC-001 | `FR-022` | `webui` | WebUiRouteAliases | route redirects | tests/env-UT | — | run: WS-A |
| `tests/unit/UT1.41_DeepLinkBlocklistAndBuildIdentity/test_w28e_1863_fix_wave_b.py` | UT | UC-001 | `FR-017`, `FR-026` | `webui` | DeepLinkBlocklistBuildIdentity | SPA deep-link gate | tests/env-UT | — | run: WS-A |
| `tests/unit/UT1.60_RuntimeContract/test_ut_runtime_contract.py` | UT | UC-001 | `NF-006` | `internal` | RuntimeContract | Python 3.13 runtime preflight (fail-closed < 3.13) | tests/env-UT | — | run: W28R-3013 |
| `tests/unit/UT_W28E1870B_ChangeStream/test_watch_criteria.py` | UT | UC-001 | `CSTREAM-FILE-001` | `internal` | ChangeWatchCriteria | glob/regex/action/backend/metadata | tests/env-UT | — | W28E-1870B |
| `tests/unit/UT_W28E1870B_ChangeStream/test_watch_rest_api.py` | UT | UC-001 | `CST-API-001`, `CSTREAM-002`, `CSTREAM-005`, `CSTREAM-009` | `api` | ChangeWatchRestApi | lifecycle/pull/recover/RBAC | tests/env-UT | — | W28E-1870B |
| `tests/unit/UT_W28E1870B_ChangeStream/test_watch_service.py` | UT | UC-001 | `CSTREAM-002`, `CSTREAM-005`–`CSTREAM-007`, `CSTREAM-009`, `CSTREAM-010`, `CSTREAM-FILE-001`, `CSTREAM-FILE-002` | `internal` | ChangeWatchService | journal/backpressure/recovery/audit/backend | tests/env-UT | — | W28E-1870B |
| `tests/unit/UT_W28E1870B_ChangeStream/test_watch_surfaces.py` | UT | UC-001 | `CSTREAM-001`, `CSTREAM-002`, `CSTREAM-009`, `CSTREAM-FILE-002` | `mcp` | ChangeWatchSurfaces | MCP/A2A/REST/capture/RBAC | tests/env-UT | — | W28E-1870B |
| `tests/integration/IT1.27_RestFileLifecycle/test_rest_file_lifecycle_http.py` | IT | UC-008 | `FR-012`, `FR-016`, `FR-017`, `FR-029`, `CS-002`, `CS-009` | `api` | RestFileLifecycleHttp | REST file contract | tests/env-IT | — | run: WS-A |
| `tests/application/AT1.14_RestFileLifecycle/test_application_rest_file_lifecycle.py` | AT | UC-002 | `FR-012`, `FR-016`, `FR-027`, `FR-029` | `api` | RestFileLifecycleWorkflow | end-to-end REST files | tests/env-AT | — | run: WS-A |
| `ST1.1_SystemAuditIntegrity` | ST | UC-018 | `NF-003` | `internal` | AuditAppendOnly | — | tests/env-ST | — | design-bound (run: Stream-B) |
| `QT_PackageCompliance` | QT | UC-002 | `NF-001` | `mcp` | PlatformPackageAdoption | — | tests/env-QT | — | design-bound (run: Stream-B) |
| `QT26_SecretsSeparation` | QT | UC-002 | `NF-002` | `mcp` | SecretConfigHygiene | — | tests/env-QT | — | design-bound (run: Stream-B) |
| `QT_LoggingCompliance` | QT | UC-006 | `NF-003` | `mcp` | LoggingAuditCompliance | — | tests/env-QT | — | design-bound (run: Stream-B) |
| `QT3_DocumentationSuite` | QT | UC-001 | `NF-004` | `mcp` | DocumentationCompleteness | — | tests/env-QT | — | design-bound (run: Stream-B) |
| `QT1_SecuritySuite` | QT | UC-001 | `NF-005` | `mcp` | SecurityPostureRules | — | tests/env-QT | — | design-bound (run: Stream-B) |
| `AT_WEBUI_EndToEnd` | AT | UC-019 | `FR-012`, `FR-016` | `webui` | WebUIBrowseSearch | — | tests/env-AT | — | design-bound (run: Stream-C) |
| `AT1.13_ApplicationWebUiAdmin` | AT | UC-024 | `FR-016`, `FR-027` | `webui` | WebUIAdminTaxonomy | — | tests/env-AT | — | design-bound (run: Stream-C) |

## 3. WebUI acceptance drive-out (Variant-V2 observations → Stream-C targets)

The W28A-651 file-mcp WebUI review (`GarysWorkingNotes.md` §"filemcpserver #2") and the
Test-Design-Audit-Jun26 SUPPLEMENT dump files (`filemcpserver/WEBUI-REVIEW.md`,
`E2E file-mcp-server.md`, `Create folder - doesnt appear.md`) carried **no ticked operator
disposition box** at ingest. Per the accepted W28E Stream-A precedent (W28E-1803A), they are treated
as **deferred WebUI feedback for Stream-C**, not as new Stream-A binding requirements — the WebUI
capabilities already exist as `FR1.37`–`FR1.47` and `FR-012`/`FR-016`/`FR-023`/`FR-024`. They are
recorded below as explicit acceptance drive-out targets so Stream-B/Stream-C have unambiguous
Playwright/E2E targets. No Playwright is authored in Stream-A.

| Obs | Source | WebUI page | Drive-out acceptance condition | Requirement(s) | Stream-C target |
|---|---|---|---|---|---|
| `WUI-FM-01` | W28A-651 Dashboard | `/` | Recent-activity uses governed DataTable with multi-delete; audit rows carry NIST/PS-40 fields; uptime is relative; connection counts agree | `FR-016`, `NF-003`, FR1.41 | `AT_WEBUI` dashboard spec |
| `WUI-FM-02` | W28A-651 / Create-folder | `/file-browser` | Storage-profile selector at top; folders/files distinguished by type icons; file metadata (size/created/modified); breadcrumb; governed bulk actions; create-file as a proper form | `FR-012`, `FR-016`, FR1.42 | `AT_WEBUI` file-browser spec |
| `WUI-FM-03` | W28A-651 Storage Profiles | `/storage-profiles` | Profiles from env/config appear with real data; CRUD + test-connection; read-only user denied (403) | `FR-016`, `CS-009`, `CS-012`, FR1.43 | `AT_WEBUI` profiles spec |
| `WUI-FM-04` | W28A-651 Search | `/search` | Profile-scoped search widget returns real path/content results; read-only cannot act beyond viewing | `FR-019`, `FR-016`, FR1.42 | `AT_WEBUI` search spec |
| `WUI-FM-05` | E2E dump | `/google-drive-settings` | OAuth config fields + connection status; only admin can modify; non-admin view-only | `FR-015`, `CS-009`, FR1.47 | `AT_WEBUI` gdrive spec |
| `WUI-FM-06` | W28A-651 MCP/A2A | `/developer/mcp-console`, `/developer/a2a-console` | Tool selection injects a parameter template; results connected to submit; API-key/auth clarity | FR1.47 | `AT_WEBUI` console specs |
| `WUI-FM-07` | W28A-651 API Docs | `/developer/api-docs` | OpenAPI rendered via Swagger/widget; MCP tool reference; service docs rendered inline | FR1.47 | `AT_WEBUI` api-docs spec |
| `WUI-FM-08` | W28A-651 Admin | `/admin/users,/groups,/api-keys,/rbac` | Populated DataTables with real data; CRUD; RBAC-aware action visibility; denial 403 | `CFG-08`–`CFG-11`, `CS-009`, FR1.47 | `AT_WEBUI` admin specs |
| `WUI-FM-09` | W28A-651 Settings | `/system/settings` | Full config shown via JsonExplorer/CodeEditor; secrets masked in inspect/edit/export | `NF-002`, FR1.47 | `AT_WEBUI` settings spec |
| `WUI-FM-10` | W28A-651 About | `/system/about` | Dialog is escapable (ok/cancel works); description accurate | FR1.47 | `AT_WEBUI` about spec |
| `WUI-FM-11` | E2E/Create-folder (CC) | `/audit-log`, Logs | File-ops audit and server logs on one governed Logs page with type filtering; NIST/PS-40 fields; 403 denials logged | `FR-022`, `NF-003` | `AT_WEBUI` logs spec; CC routed to W28E-1825 if cross-cutting |
| `WUI-FM-12` | W28A-651 session | all | WebUI session does not die on key failure; 401/403 forces clean re-auth, never fake success | `FR-023`, `FR-024` | `AT_WEBUI` session-resilience spec |

## 4. Test-design rules (binding, applied in W28E-1802A)

1. One primary test per FR-NNN; variants via `pytest.parametrize` (recorded in the `Variants` column).
2. Common scenarios (login, RBAC matrix, anon-denied) shared via helpers, not duplicated.
3. Cross-surface FRs use parametrized test files, not duplicate files.
4. Every `surface: webui` FR drives a Stream-C Playwright target (cookie-login + RBAC matrix + screenshot + DOM-assert + console-error-gate + CW-pattern) — see §3.
5. Every `surface: api|mcp|a2a` FR has a protocol-level test.
6. Every `CS-NNN` binds to a negative test with the expected denial code (see REQUIREMENTS.md §5).
7. CRUD-applicable entities (storage profiles, users, groups, API keys) have C/R/U/D coverage.
8. W28C-1711-R3 `@pytest.mark.probe` orphans were rebound to semantic `@pytest.mark.req(...)`;
   no probe markers remain (`tests/conftest.py` enforces tier + surface + `req()` on every test).


<!-- W28E-1854 PS-PREPROD-DEPLOY-SMOKE rollout (2026-06-29) -->

## W28E-1854 — PS-PREPROD-DEPLOY-SMOKE (preprod deployment smoke)

Binding standard: `cloud-dog-ai-platform-standards/docs/standards/PS-PREPROD-DEPLOY-SMOKE.md`
(PDS-001..PDS-013 + sibling sentinels). Lesson origin: AGENT-LESSONS §6.157 — a
deployed service can answer health checks while its WebUI login flow crashes blank
post-login. Health-only / route-only / local-only proof is NOT acceptance; this
gate runs a real browser AFTER the final deployed digest is live.

- **Smoke command (service entry point):**
  `E2E_WEB_PASSWORD="<approved preprod admin password>" bash tests/smoke/run-preprod-deploy-smoke.sh`
- **SSOT spec:** `cloud-dog-ai-ui-monorepo/apps/file-mcp/tests/e2e/preprod-deploy-smoke.spec.ts`
- **Dedicated Playwright config (no local webServer):** `cloud-dog-ai-ui-monorepo/apps/file-mcp/playwright.preprod-smoke.config.ts`
- **Required config keys (no hardcoded secrets):** `E2E_BASE_URL`
  (default `https://filemcpserver0.cloud-dog.net`), `E2E_WEB_USERNAME` (default `admin`),
  `E2E_WEB_PASSWORD` / `CLOUD_DOG_WEB_LOGIN_PASSWORD` (approved preprod env / Vault
  `cloud_dog_ai/config:dev.services.filemcpserver0.web_password`).
- **Expected auth mode:** cookie session login at canonical `/login`
  (`/ui/login` → 308 → `/login`); anonymous `/auth/me` → 401 or `{user:null}` (no principal leak).
- **Canonical page inventory (PDS-009):** `/`, `/admin/users`, `/admin/groups`,
  `/admin/api-keys`, `/admin/roles`, `/admin/rbac`, `/audit-log`, `/system/settings`,
  `/system/jobs`, `/developer/api-docs`, `/developer/mcp-console`,
  `/developer/a2a-console`, `/system/about`.
- **Service-specific page inventory (PDS-010, hard-navigated — the crash-class guard):**
  `/file-browser`, `/storage-profiles`, `/search`, `/google-drive-settings`.
- **Cleanliness bar (PDS-012):** zero uncaught page errors, zero fatal console
  errors, zero 5xx, zero unexpected 4xx (shared `@cloud-dog/idam` best-effort
  capability probes are the only tolerated 4xx; the crash discriminator
  pageerror + blank `#root` + 5xx is asserted with zero tolerance).
- **Evidence output location:** `working/preprod-deploy-smoke/` (gitignored test
  output: JUnit `preprod-deploy-smoke.junit.xml`, HTML report, traces, screenshots).
