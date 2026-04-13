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

## Standard Commands
```bash
python3 -m pytest tests/quality --env tests/env-QT -q
python3 -m pytest tests/unit --env tests/env-UT -q
python3 -m pytest tests/system --env tests/env-ST -q
python3 -m pytest tests/integration --env tests/env-IT -q
python3 -m pytest tests/application --env tests/env-AT -q
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
