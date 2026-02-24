# File MCP Server Test Catalogue

## Latest Verified Execution (2026-02-23)

| Tier | Command | Result |
|---|---|---|
| UT | `python3 -m pytest tests/unit/ --env tests/env-UT -v --tb=short` | `122 passed, 1 skipped, 0 failed` |
| ST | `python3 -m pytest tests/system/ --env tests/env-ST -v --tb=short` | `21 passed, 0 skipped, 0 failed` |
| IT | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a; python3 -m pytest tests/integration/ --env tests/env-IT -v --tb=short` | `29 passed, 16 skipped, 0 failed` |
| AT | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a; python3 -m pytest tests/application/ --env tests/env-IT -v --tb=short` | `8 passed, 1 skipped, 0 failed` |
| Total | Tiered suite above | `180 passed, 18 skipped, 0 failed` |

## Migration Verification Scripts (2026-02-23)

| Script | Result |
|---|---|
| `migration/verify/verify-file-mcp-server-CONFIG.sh` | `14/14 PASS` |
| `migration/verify/verify-file-mcp-server-LOGGING.sh` | `15/15 PASS` |
| `migration/verify/verify-file-mcp-server-API-KIT.sh` | `17/17 PASS` |
| `migration/verify/verify-file-mcp-server-IDAM.sh` | `15/15 PASS` |

## Mock/Stub Audit (RULES.md §5.5)

| File | Tier | Outcome |
|---|---|---|
| `test_api_kit_contract.py` | UT | Uses in-process test doubles only; allowed in UT. |
| `test_google_drive_admin.py` | UT | Uses monkeypatching for isolated OAuth/admin logic; allowed in UT. |
| `test_server_runtime.py` | UT | Uses in-process middleware/app harnessing; allowed in UT. |
| `test_system_conversion_backend_selection.py` | IT | Reclassified to IT because it boots a real server and performs HTTP MCP calls. |
| `test_webdav_storage.py` | UT | Uses monkeypatching for backend unit logic; allowed in UT. |

## UT Catalogue

| ID Folder | Module | What Is Tested |
|---|---|---|
| `UT1.10_Filesystem` | `test_filesystem.py` | Filesystem utility tests |
| `UT1.11_GoogleDriveAdmin` | `test_google_drive_admin.py` | Tests for server-hosted Google Drive admin flow helpers |
| `UT1.12_GoogleDriveOauthHelper` | `test_google_drive_oauth_helper.py` | Tests for Google Drive OAuth helper script |
| `UT1.13_GoogleDriveSetupScript` | `test_google_drive_setup_script.py` | Unit tests for interactive Google Drive setup script helpers |
| `UT1.14_GoogleDriveStorage` | `test_google_drive_storage.py` | Google Drive storage unit tests |
| `UT1.15_Lifecycle` | `test_lifecycle.py` | Lifecycle |
| `UT1.16_Observability` | `test_observability.py` | Observability helper tests |
| `UT1.17_Posix` | `test_posix.py` | POSIX portability tests |
| `UT1.18_ScopePolicy` | `test_scope_policy.py` | Scope policy |
| `UT1.19_Search` | `test_search.py` | Search utility tests |
| `UT1.1_ApiKitContract` | `test_api_kit_contract.py` | Api kit contract |
| `UT1.20_Sedlike` | `test_sedlike.py` | Sed-like edit tests |
| `UT1.21_ServerDispatch` | `test_server_dispatch.py` | Server dispatch |
| `UT1.22_ServerRuntime` | `test_server_runtime.py` | Server runtime |
| `UT1.23_ToolReuse` | `test_tool_reuse.py` | Tool reuse tests |
| `UT1.24_ToolsRegistry` | `test_tools_registry.py` | Tool registry tests |
| `UT1.25_Validate` | `test_validate.py` | Validation policy tests |
| `UT1.26_WebdavStorage` | `test_webdav_storage.py` | WebDAV backend unit tests |
| `UT1.2_Audit` | `test_audit.py` | Audit |
| `UT1.3_Auth` | `test_auth.py` | Auth |
| `UT1.4_ConfigLoader` | `test_config_loader.py` | Config loader tests |
| `UT1.5_Convert` | `test_convert.py` | Conversion pipeline tests |
| `UT1.6_Diff` | `test_diff.py` | Diff utility tests |
| `UT1.7_EditStructured` | `test_edit_structured.py` | Structured edit tests |
| `UT1.8_Encoding` | `test_encoding.py` | Base64 encoding tests |
| `UT1.9_EndpointHealth` | `test_endpoint_health.py` | Endpoint health manager tests |

## ST Catalogue

| ID Folder | Module | What Is Tested |
|---|---|---|
| `ST1.10_SystemLimitsTimeout` | `test_system_limits_timeout.py` | System limits timeout |
| `ST1.11_SystemReadPartialRanges` | `test_system_read_partial_ranges.py` | System read partial ranges |
| `ST1.12_SystemSedTransactionContract` | `test_system_sed_transaction_contract.py` | System sed transaction contract |
| `ST1.13_SystemSnapshotRetention` | `test_system_snapshot_retention.py` | System snapshot retention |
| `ST1.14_SystemStructuredPathEdgeCases` | `test_system_structured_path_edge_cases.py` | System structured path edge cases |
| `ST1.15_SystemStructuredRollbackContract` | `test_system_structured_rollback_contract.py` | System structured rollback contract |
| `ST1.16_SystemValidateFileTool` | `test_system_validate_file_tool.py` | System validate file tool |
| `ST1.1_SystemAuditIntegrity` | `test_system_audit_integrity.py` | System audit integrity |
| `ST1.2_SystemAuthHealth` | `test_system_auth_health.py` | System auth health |
| `ST1.3_SystemConversionMatrix` | `test_system_conversion_matrix.py` | System conversion matrix |
| `ST1.4_SystemConversionOptionality` | `test_system_conversion_optionality.py` | System conversion optionality |
| `ST1.5_SystemConversionRealBackends` | `test_system_conversion_real_backends.py` | System conversion real backends |
| `ST1.6_SystemDryRunContract` | `test_system_dry_run_contract.py` | System dry run contract |
| `ST1.7_SystemEndpointRestartThreshold` | `test_system_endpoint_restart_threshold.py` | System tests for endpoint health restart threshold behavior |
| `ST1.8_SystemErrorContract` | `test_system_error_contract.py` | System error contract |
| `ST1.9_SystemLimits` | `test_system_limits.py` | System limits |

## IT Catalogue

| ID Folder | Module | What Is Tested |
|---|---|---|
| `IT1.10_IntegrationMarkdownAdvancedHttp` | `test_integration_markdown_advanced_http.py` | Integration markdown advanced http |
| `IT1.11_IntegrationMeldOptionalityHttp` | `test_integration_meld_optionality_http.py` | Integration meld optionality http |
| `IT1.12_IntegrationMultiProfileRoutingHttp` | `test_integration_multi_profile_routing_http.py` | Integration multi profile routing http |
| `IT1.13_IntegrationRemoteBackendToolMatrixHttp` | `test_integration_remote_backend_tool_matrix_http.py` | Remote backend MCP tool matrix integration tests |
| `IT1.14_IntegrationRemoteStorageBackendsHttp` | `test_integration_remote_storage_backends_http.py` | Integration remote storage backends http |
| `IT1.15_IntegrationScopedOps` | `test_integration_scoped_ops.py` | Integration scoped ops |
| `IT1.16_IntegrationSearchHttp` | `test_integration_search_http.py` | Integration search http |
| `IT1.17_IntegrationSedlikeFileHttp` | `test_integration_sedlike_file_http.py` | Integration sedlike file http |
| `IT1.18_IntegrationSedlikeTransactionHttp` | `test_integration_sedlike_transaction_http.py` | Integration sedlike transaction http |
| `IT1.19_IntegrationStoryMultitypeCrudHttp` | `test_integration_story_multitype_crud_http.py` | Integration story multitype crud http |
| `IT1.1_DockerContainerRemoteStorageBackends` | `test_docker_container_remote_storage_backends.py` | Docker container remote storage backend tests |
| `IT1.20_IntegrationStructuredAuditSnapshot` | `test_integration_structured_audit_snapshot.py` | Integration structured audit snapshot |
| `IT1.21_IntegrationStructuredFormats` | `test_integration_structured_formats.py` | Integration structured formats |
| `IT1.22_IntegrationYamlFileStructuredOps` | `test_integration_yaml_file_structured_ops.py` | Integration yaml file structured ops |
| `IT1.23_ServerHttpIntegration` | `test_server_http_integration.py` | Server http integration |
| `IT1.24_SystemConversionBackendSelection` | `test_system_conversion_backend_selection.py` | System conversion backend selection |
| `IT1.2_DockerContainerRuntime` | `test_docker_container_runtime.py` | Docker container runtime tests |
| `IT1.3_IntegrationBase64FileOps` | `test_integration_base64_file_ops.py` | Integration base64 file ops |
| `IT1.4_IntegrationConfigMatrixHarnessHttp` | `test_integration_config_matrix_harness_http.py` | Integration config matrix harness http |
| `IT1.5_IntegrationDiffFilesHttp` | `test_integration_diff_files_http.py` | Integration diff files http |
| `IT1.6_IntegrationFilesystemPathToolsHttp` | `test_integration_filesystem_path_tools_http.py` | Integration filesystem path tools http |
| `IT1.7_IntegrationGoogleDriveLiveHttp` | `test_integration_google_drive_live_http.py` | Live Google Drive backend integration tests |
| `IT1.8_IntegrationIterativeCycleGuardHttp` | `test_integration_iterative_cycle_guard_http.py` | Integration iterative cycle guard http |
| `IT1.9_IntegrationJsonYamlGetMergeHttp` | `test_integration_json_yaml_get_merge_http.py` | Integration json yaml get merge http |

## AT Catalogue

| ID Folder | Module | What Is Tested |
|---|---|---|
| `AT1.1_ApplicationCompoundReleaseWorkflow` | `test_application_compound_release_workflow.py` | Application compound release workflow |
| `AT1.2_ApplicationConversionEditWorkflow` | `test_application_conversion_edit_workflow.py` | Application conversion edit workflow |
| `AT1.3_ApplicationConversionStructuredWorkflow` | `test_application_conversion_structured_workflow.py` | Application conversion structured workflow |
| `AT1.4_ApplicationLifecycleWorkflow` | `test_application_lifecycle_workflow.py` | Application lifecycle workflow |
| `AT1.5_ApplicationMultifileTransactionWorkflow` | `test_application_multifile_transaction_workflow.py` | Application multifile transaction workflow |
| `AT1.6_ApplicationPreprodProfileChainHttp` | `test_application_preprod_profile_chain_http.py` | Application preprod profile chain http |
| `AT1.7_ApplicationSafeEditWorkflow` | `test_application_safe_edit_workflow.py` | Application safe edit workflow |
| `AT1.8_ApplicationSearchEditAuditWorkflow` | `test_application_search_edit_audit_workflow.py` | Application search edit audit workflow |
| `AT1.9_ApplicationSecurityBoundary` | `test_application_security_boundary.py` | Application security boundary |

