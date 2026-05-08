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
- `test_config_loader.py`
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
| CFG-08..CFG-11 (User/Group/Key mgmt) | `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | `test_it1_26_user_key_profile_lifecycle_supports_mcp_file_operations` | COVERED |
| CFG-13 (Admin-only CRUD) | `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | (admin gating verified in lifecycle workflow) | COVERED |
| FR1.37 (Web UI Routes) | `tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py` | AT_WEBUI suite | COVERED |
| FR1.44 (Web UI Accessibility) | `tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py` | AT1.13 suite | COVERED |
| FR1.47 (Web UI Standards Merge) | `tests/application/AT_WEBUI_EndToEnd/test_webui_end_to_end.py` + `tests/application/AT1.13_ApplicationWebUiAdmin/test_application_webui_admin.py` | WebUI end-to-end and admin WebUI suites | COVERED |
| CFG-06 (A2A broadcast) | `tests/unit/UT_CFG06_A2AEvents/test_config_change_events.py` + `tests/integration/IT_CFG06_A2AEvents/test_a2a_events_integration.py` | UT_CFG06_A2AEvents + IT_CFG06_A2AEvents | IMPLEMENTED |
| CFG-12 (Audit logging for CRUD) | `tests/unit/UT1.2_Audit/test_audit.py` + `tests/unit/UT_AuditLogFormat/test_audit_log_format.py` + `tests/integration/IT1.20_IntegrationStructuredAuditSnapshot/test_integration_structured_audit_snapshot.py` + `tests/integration/IT1.26_IntegrationConfigCrudIdentityWorkflow/test_integration_config_crud_identity_workflow.py` | `test_audit_logger_writes`, `test_audit_logger_uses_explicit_actor_identity`, `test_audit_event_has_all_au3_fields`, `test_structured_edit_with_audit_and_snapshot`, `test_it1_26_user_key_profile_lifecycle_supports_mcp_file_operations` (platform capability via `cloud_dog_logging.AuditLogger.log_crud`, wrapped by `file_tools.audit.adapter.AuditLogger`) | IMPLEMENTED |
| FR1.32 (Google Drive OAuth Folder Binding) | `tests/application/AT1.12_GoogleDriveOauthLive/test_google_drive_oauth_live.py` | AT1.12 suite | COVERED |
