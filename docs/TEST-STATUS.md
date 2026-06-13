---
template-id: T-TSS
template-version: 1.0
project: file-mcp-server
doc-last-updated: 2026-06-13T10:59:11.209949+00:00
doc-git-commit: d893dd83bd865d6699918b9ceecd2ae53e1f873e
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-06-13T10:59:11.209949+00:00
---

# file-mcp-server — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-06-13T10:59:11.209949+00:00
- **Commit:** `d893dd83bd865d6699918b9ceecd2ae53e1f873e` (`main`)
- **Totals:** 124 tests | 64 passed | 59 failed | 1 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `::tests.unit.UT1.12_GoogleDriveOauthHelper.test_w28c_1702_fm6_anon_gate` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.1_ApiKitContract.test_api_kit_contract` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.21_ServerDispatch.test_server_dispatch` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.22_ServerRuntime.test_server_runtime` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.30_AdminIdentity.test_admin_identity` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.33_W28C1702.test_w28c_1702_forensic_fixes` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.35_FlatRoleLogin.test_flat_role_login` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `::tests.unit.UT1.3_Auth.test_auth` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.10_ApplicationA2AAuthWorkflow.test_application_a2a_auth_workflow::test_application_a2a_health_flow_uses_test_a2a_api_key` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.11_DynamicProfileCRUDLifecycle.test_dynamic_profile_crud_lifecycle::test_at1_11_dynamic_profile_crud_lifecycle` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.12_GoogleDriveOauthLive.test_google_drive_oauth_live::test_google_oauth_live_exchange_if_enabled` | UT/ST/IT | skip | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.13_ApplicationWebUiAdmin.test_application_webui_admin::test_at1_13_webui_admin_pages_render_profile_and_identity_data` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.1_ApplicationCompoundReleaseWorkflow.test_application_compound_release_workflow::test_application_compound_release_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.2_ApplicationConversionEditWorkflow.test_application_conversion_edit_workflow::test_conversion_plus_markdown_edit_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.3_ApplicationConversionStructuredWorkflow.test_application_conversion_structured_workflow::test_application_conversion_structured_diff_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.4_ApplicationLifecycleWorkflow.test_application_lifecycle_workflow::test_operator_lifecycle_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.5_ApplicationMultifileTransactionWorkflow.test_application_multifile_transaction_workflow::test_application_multifile_transaction_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.6_ApplicationPreprodProfileChainHttp.test_application_preprod_profile_chain_http::test_application_preprod_profile_chain_flow_live` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.7_ApplicationSafeEditWorkflow.test_application_safe_edit_workflow::test_end_to_end_safe_edit_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.8_ApplicationSearchEditAuditWorkflow.test_application_search_edit_audit_workflow::test_application_search_edit_audit_workflow` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT1.9_ApplicationSecurityBoundary.test_application_security_boundary::test_security_boundary_enforcement_with_audit` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_PROFILE_LIFECYCLE.test_profile_lifecycle::test_profile_lifecycle_project_folder_with_dated_content` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_ProfileCRUD.test_profile_crud::test_at_profile_crud_lifecycle` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t10_dashboard` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t11_edit_file` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t1_api_key_login` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t2_user_crud` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t3_group_crud` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t4_api_key_crud` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t5_rbac_assign_verify_remove` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t6_read_file` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t7_search` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t8_audit_log` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t9_storage_profile_crud` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt1_security_suite::test_qt1_1_secrets_never_logged` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt1_security_suite::test_qt1_2_path_traversal_prevention` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt1_security_suite::test_qt1_3_domain_specific_safety` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt1_security_suite::test_qt1_4_uk_english_compliance` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt26_secrets_separation::test_qt2_6_defaults_config_do_not_embed_plain_secrets` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt26_secrets_separation::test_qt2_6_no_hardcoded_secrets_in_source` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt26_secrets_separation::test_qt2_6_sensitive_env_values_use_vault_or_scoped_files` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt27_bespoke_code_scan::test_qt2_7_no_bespoke_platform_replacements` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt3_documentation_suite::test_qt3_1_required_files_exist` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt3_documentation_suite::test_qt3_2_requirement_id_format` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt3_documentation_suite::test_qt3_3_test_id_uniqueness` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_bespoke_auth` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_os_environ_for_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_raw_fastapi` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_yaml_safe_load_for_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_api_uses_cloud_dog_api_kit` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_auth_uses_cloud_dog_idam` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_config_uses_cloud_dog_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_logging_uses_cloud_dog_logging` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_no_bespoke_db_access` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_no_bespoke_llm_calls` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_no_bespoke_vdb_calls` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_package_adoption::test_pyproject_declares_platform_packages` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_requirement_traceability_manifest::test_manifest_covers_all_requirements` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_requirement_traceability_manifest::test_manifest_entries_not_empty` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_requirement_traceability_manifest::test_manifest_mapped_paths_exist` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_file_headers_present` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_functions_have_docstrings` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_no_direct_external_imports` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_no_hardcoded_credentials` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_no_hardcoded_urls` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_no_mock_in_it_at` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_no_skip_calls_in_it_at` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_all_requirements_have_code` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_all_requirements_have_tests` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_all_tests_have_requirements` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_delivery_matrix_complete` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_no_orphan_test_files` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_config_yaml_no_secrets` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_defaults_yaml_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_defaults_yaml_no_secrets` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_env_files_exist_per_tier` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_env_files_use_vault_expressions` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_no_secrets_in_source` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_LoggingCompliance.test_logging_compliance::test_audit_events_doc_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_integrity_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_retention_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_rotation_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_licence_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_auth` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_config_manager` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_logging` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_direct_llm_calls` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_hardcoded_secrets` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_internal_hostnames` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_memory_queue` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_readme_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_runtime_config_endpoint` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_server_control_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_ui_dist_exists` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.10_SystemLimitsTimeout.test_system_limits_timeout::test_limits_timeout_path_for_conversion` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.11_SystemReadPartialRanges.test_system_read_partial_ranges::test_read_file_partial_line_and_byte_ranges` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.11_SystemReadPartialRanges.test_system_read_partial_ranges::test_read_file_rejects_mixed_line_and_byte_ranges` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.12_SystemSedTransactionContract.test_system_sed_transaction_contract::test_sed_transaction_contract_validation_and_noop` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.12_SystemSedTransactionContract.test_system_sed_transaction_contract::test_sed_transaction_ordering_and_policy_variants` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.13_SystemSnapshotRetention.test_system_snapshot_retention::test_snapshot_retention_prunes_old_snapshot_dirs` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.14_SystemStructuredPathEdgeCases.test_system_structured_path_edge_cases::test_structured_nested_list_dict_and_root_merge_paths` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.14_SystemStructuredPathEdgeCases.test_system_structured_path_edge_cases::test_structured_path_edge_cases_and_negative_contract` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.15_SystemStructuredRollbackContract.test_system_structured_rollback_contract::test_structured_failed_mutation_is_rolled_back_and_audited` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.16_SystemValidateFileTool.test_system_validate_file_tool::test_validate_file_tool_success_and_type_inference` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.16_SystemValidateFileTool.test_system_validate_file_tool::test_validate_file_tool_unsupported_extension_fails` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration::test_st_db_01_migration_upgrade_on_fresh_sqlite` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration::test_st_db_02_crud_via_session_manager` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration_multibackend::test_st_db_03_migration_lifecycle_upgrade_downgrade_upgrade` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration_multibackend::test_st_db_04_schema_versioning_simulation` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.1_SystemAuditIntegrity.test_system_audit_integrity::test_audit_log_integrity_append_only` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.2_SystemAuthHealth.test_system_auth_health::test_auth_enforcement_and_health` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.3_SystemConversionMatrix.test_system_conversion_matrix::test_conversion_response_matrix_fields` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.4_SystemConversionOptionality.test_system_conversion_optionality::test_conversion_missing_backend_returns_warning` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.5_SystemConversionRealBackends.test_system_conversion_real_backends::test_real_libreoffice_backend_conversion` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.5_SystemConversionRealBackends.test_system_conversion_real_backends::test_real_pandoc_backend_conversion` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.6_SystemDryRunContract.test_system_dry_run_contract::test_dry_run_mutations_do_not_change_files_and_are_audited` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.7_SystemEndpointRestartThreshold.test_system_endpoint_restart_threshold::test_server_exits_when_restart_threshold_reached` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.8_SystemErrorContract.test_system_error_contract::test_error_contract_for_expected_operational_failures` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST1.9_SystemLimits.test_system_limits::test_limits_search_and_conversion_size` | UT/ST/IT | fail | 2026-06-13 | `d893dd83` | |
| `tests.system.ST_IntegrityVerifier.test_integrity_running::test_integrity_log_file_populated` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.system.ST_IntegrityVerifier.test_integrity_running::test_integrity_record_fields` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.system.ST_IntegrityVerifier.test_integrity_running::test_integrity_verifier_starts_with_server` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.system.ST_LogRotation.test_rotation_config::test_rotation_handler_configured` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |
| `tests.system.ST_LogRotation.test_rotation_config::test_rotation_parameters_from_config` | UT/ST/IT | pass | 2026-06-13 | `d893dd83` | |

## 3. Failures (detail)

- `tests.system.ST1.10_SystemLimitsTimeout.test_system_limits_timeout::test_limits_timeout_path_for_conversion`: RuntimeError: Health check timed out: ['http://127.0.0.1:50819/app/v1/health', 'http://127.0.0.1:50819/health']
- `tests.system.ST1.11_SystemReadPartialRanges.test_system_read_partial_ranges::test_read_file_partial_line_and_byte_ranges`: RuntimeError: Health check timed out: ['http://127.0.0.1:48879/app/v1/health', 'http://127.0.0.1:48879/health']
- `tests.system.ST1.11_SystemReadPartialRanges.test_system_read_partial_ranges::test_read_file_rejects_mixed_line_and_byte_ranges`: RuntimeError: Health check timed out: ['http://127.0.0.1:59303/app/v1/health', 'http://127.0.0.1:59303/health']
- `tests.system.ST1.12_SystemSedTransactionContract.test_system_sed_transaction_contract::test_sed_transaction_contract_validation_and_noop`: RuntimeError: Health check timed out: ['http://127.0.0.1:55017/app/v1/health', 'http://127.0.0.1:55017/health']
- `tests.system.ST1.12_SystemSedTransactionContract.test_system_sed_transaction_contract::test_sed_transaction_ordering_and_policy_variants`: RuntimeError: Health check timed out: ['http://127.0.0.1:54737/app/v1/health', 'http://127.0.0.1:54737/health']
- `tests.system.ST1.13_SystemSnapshotRetention.test_system_snapshot_retention::test_snapshot_retention_prunes_old_snapshot_dirs`: RuntimeError: Health check timed out: ['http://127.0.0.1:32857/app/v1/health', 'http://127.0.0.1:32857/health']
- `tests.system.ST1.14_SystemStructuredPathEdgeCases.test_system_structured_path_edge_cases::test_structured_path_edge_cases_and_negative_contract`: RuntimeError: Health check timed out: ['http://127.0.0.1:43799/app/v1/health', 'http://127.0.0.1:43799/health']
- `tests.system.ST1.14_SystemStructuredPathEdgeCases.test_system_structured_path_edge_cases::test_structured_nested_list_dict_and_root_merge_paths`: RuntimeError: Health check timed out: ['http://127.0.0.1:36607/app/v1/health', 'http://127.0.0.1:36607/health']
- `tests.system.ST1.15_SystemStructuredRollbackContract.test_system_structured_rollback_contract::test_structured_failed_mutation_is_rolled_back_and_audited`: RuntimeError: Health check timed out: ['http://127.0.0.1:44717/app/v1/health', 'http://127.0.0.1:44717/health']
- `tests.system.ST1.16_SystemValidateFileTool.test_system_validate_file_tool::test_validate_file_tool_success_and_type_inference`: RuntimeError: Health check timed out: ['http://127.0.0.1:36959/app/v1/health', 'http://127.0.0.1:36959/health']
- `tests.system.ST1.16_SystemValidateFileTool.test_system_validate_file_tool::test_validate_file_tool_unsupported_extension_fails`: RuntimeError: Health check timed out: ['http://127.0.0.1:37187/app/v1/health', 'http://127.0.0.1:37187/health']
- `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration::test_st_db_01_migration_upgrade_on_fresh_sqlite`: ModuleNotFoundError: No module named 'cloud_dog_idam'
- `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration::test_st_db_02_crud_via_session_manager`: ModuleNotFoundError: No module named 'cloud_dog_idam'
- `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration_multibackend::test_st_db_03_migration_lifecycle_upgrade_downgrade_upgrade`: ModuleNotFoundError: No module named 'cloud_dog_idam'
- `tests.system.ST1.17_SystemDatabaseMigration.test_database_migration_multibackend::test_st_db_04_schema_versioning_simulation`: ModuleNotFoundError: No module named 'cloud_dog_idam'
- `tests.system.ST1.1_SystemAuditIntegrity.test_system_audit_integrity::test_audit_log_integrity_append_only`: RuntimeError: Health check timed out: ['http://127.0.0.1:47841/app/v1/health', 'http://127.0.0.1:47841/health']
- `tests.system.ST1.2_SystemAuthHealth.test_system_auth_health::test_auth_enforcement_and_health`: RuntimeError: Health check timed out: ['http://127.0.0.1:54347/app/v1/health', 'http://127.0.0.1:54347/health']
- `tests.system.ST1.3_SystemConversionMatrix.test_system_conversion_matrix::test_conversion_response_matrix_fields`: RuntimeError: Health check timed out: ['http://127.0.0.1:60005/app/v1/health', 'http://127.0.0.1:60005/health']
- `tests.system.ST1.4_SystemConversionOptionality.test_system_conversion_optionality::test_conversion_missing_backend_returns_warning`: RuntimeError: Health check timed out: ['http://127.0.0.1:56193/app/v1/health', 'http://127.0.0.1:56193/health']
- `tests.system.ST1.5_SystemConversionRealBackends.test_system_conversion_real_backends::test_real_pandoc_backend_conversion`: RuntimeError: Health check timed out: ['http://127.0.0.1:42575/app/v1/health', 'http://127.0.0.1:42575/health']
- `tests.system.ST1.5_SystemConversionRealBackends.test_system_conversion_real_backends::test_real_libreoffice_backend_conversion`: RuntimeError: Health check timed out: ['http://127.0.0.1:36605/app/v1/health', 'http://127.0.0.1:36605/health']
- `tests.system.ST1.6_SystemDryRunContract.test_system_dry_run_contract::test_dry_run_mutations_do_not_change_files_and_are_audited`: RuntimeError: Health check timed out: ['http://127.0.0.1:38227/app/v1/health', 'http://127.0.0.1:38227/health']
- `tests.system.ST1.7_SystemEndpointRestartThreshold.test_system_endpoint_restart_threshold::test_server_exits_when_restart_threshold_reached`: AssertionError: assert 1 == 76
 +  where 1 = CompletedProcess(args=['/opt/iac/Development/cloud-dog-ai/file-mcp-server/.venv/bin/python', '-m', 'file_mcp_server', ...n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- `tests.system.ST1.8_SystemErrorContract.test_system_error_contract::test_error_contract_for_expected_operational_failures`: RuntimeError: Health check timed out: ['http://127.0.0.1:49561/app/v1/health', 'http://127.0.0.1:49561/health']
- `tests.system.ST1.9_SystemLimits.test_system_limits::test_limits_search_and_conversion_size`: RuntimeError: Health check timed out: ['http://127.0.0.1:57559/app/v1/health', 'http://127.0.0.1:57559/health']
- `tests.quality.QT_COMPLIANCE.test_qt_rules_compliance::test_file_headers_present`: AssertionError: Missing file headers:
  - src/file_mcp_server/guard.py:1 :: missing module header/docstring with License
  - src/file_mcp_server/idam_seam.py:1 :: missing module header/docstring with 
- `tests.quality.QT_COMPLIANCE.test_qt_traceability::test_no_orphan_test_files`: AssertionError: Test files missing from docs/TESTS.md:
  - tests/smoke/SM1.2_NoUnguardedRoute/test_no_unguarded_route_meta.py
assert not ['tests/smoke/SM1.2_NoUnguardedRoute/test_no_unguarded_route_me
- `tests.application.AT1.10_ApplicationA2AAuthWorkflow.test_application_a2a_auth_workflow::test_application_a2a_health_flow_uses_test_a2a_api_key`: RuntimeError: Health check timed out: ['http://127.0.0.1:48043/app/v1/health', 'http://127.0.0.1:48043/health']
- `tests.application.AT1.11_DynamicProfileCRUDLifecycle.test_dynamic_profile_crud_lifecycle::test_at1_11_dynamic_profile_crud_lifecycle`: RuntimeError: Health check timed out: ['http://127.0.0.1:53027/app/v1/health', 'http://127.0.0.1:53027/health']
- `tests.application.AT1.13_ApplicationWebUiAdmin.test_application_webui_admin::test_at1_13_webui_admin_pages_render_profile_and_identity_data`: RuntimeError: Health check timed out: ['http://127.0.0.1:43129/app/v1/health', 'http://127.0.0.1:43129/health']
- `tests.application.AT1.1_ApplicationCompoundReleaseWorkflow.test_application_compound_release_workflow::test_application_compound_release_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:43175/app/v1/health', 'http://127.0.0.1:43175/health']
- `tests.application.AT1.2_ApplicationConversionEditWorkflow.test_application_conversion_edit_workflow::test_conversion_plus_markdown_edit_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:59789/app/v1/health', 'http://127.0.0.1:59789/health']
- `tests.application.AT1.3_ApplicationConversionStructuredWorkflow.test_application_conversion_structured_workflow::test_application_conversion_structured_diff_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:46259/app/v1/health', 'http://127.0.0.1:46259/health']
- `tests.application.AT1.4_ApplicationLifecycleWorkflow.test_application_lifecycle_workflow::test_operator_lifecycle_workflow`: AssertionError: Traceback (most recent call last):
    File "<frozen runpy>", line 198, in _run_module_as_main
    File "<frozen runpy>", line 88, in _run_code
    File "/opt/iac/Development/cloud-dog
- `tests.application.AT1.5_ApplicationMultifileTransactionWorkflow.test_application_multifile_transaction_workflow::test_application_multifile_transaction_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:37209/app/v1/health', 'http://127.0.0.1:37209/health']
- `tests.application.AT1.7_ApplicationSafeEditWorkflow.test_application_safe_edit_workflow::test_end_to_end_safe_edit_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:52007/app/v1/health', 'http://127.0.0.1:52007/health']
- `tests.application.AT1.8_ApplicationSearchEditAuditWorkflow.test_application_search_edit_audit_workflow::test_application_search_edit_audit_workflow`: RuntimeError: Health check timed out: ['http://127.0.0.1:35083/app/v1/health', 'http://127.0.0.1:35083/health']
- `tests.application.AT1.9_ApplicationSecurityBoundary.test_application_security_boundary::test_security_boundary_enforcement_with_audit`: RuntimeError: Health check timed out: ['http://127.0.0.1:46417/app/v1/health', 'http://127.0.0.1:46417/health']
- `tests.application.AT_PROFILE_LIFECYCLE.test_profile_lifecycle::test_profile_lifecycle_project_folder_with_dated_content`: RuntimeError: Health check timed out: ['http://127.0.0.1:33733/app/v1/health', 'http://127.0.0.1:33733/health']
- `tests.application.AT_ProfileCRUD.test_profile_crud::test_at_profile_crud_lifecycle`: RuntimeError: Health check timed out: ['http://127.0.0.1:43327/app/v1/health', 'http://127.0.0.1:43327/health']
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t1_api_key_login`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t2_user_crud`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t3_group_crud`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t4_api_key_crud`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t5_rbac_assign_verify_remove`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t6_read_file`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t7_search`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t8_audit_log`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t9_storage_profile_crud`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t10_dashboard`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `tests.application.AT_WEBUI_EndToEnd.test_webui_end_to_end::test_webui_t11_edit_file`: failed on setup with "playwright._impl._errors.Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8061/login
Call log:
  - navigating to "http://127.0.0.1:8061/login", waiting until "do
- `::tests.unit.UT1.12_GoogleDriveOauthHelper.test_w28c_1702_fm6_anon_gate`: collection failure
- `::tests.unit.UT1.1_ApiKitContract.test_api_kit_contract`: collection failure
- `::tests.unit.UT1.21_ServerDispatch.test_server_dispatch`: collection failure
- `::tests.unit.UT1.22_ServerRuntime.test_server_runtime`: collection failure
- `::tests.unit.UT1.30_AdminIdentity.test_admin_identity`: collection failure
- `::tests.unit.UT1.33_W28C1702.test_w28c_1702_forensic_fixes`: collection failure
- `::tests.unit.UT1.35_FlatRoleLogin.test_flat_role_login`: collection failure
- `::tests.unit.UT1.3_Auth.test_auth`: collection failure
