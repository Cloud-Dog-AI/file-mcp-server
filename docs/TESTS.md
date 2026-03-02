# File MCP Server Test Catalogue

## Latest W14B-04 Status (2026-03-01)

- Instruction file used:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14B-04-FILE-MCP-A2A-ENABLE-AUTH-CONTRACT-STRICT.md`
- Hard-stop prechecks:
  - `GET /a2a/health` without auth -> `401`
  - `GET /a2a/health` with `Authorization: Bearer 12345678` -> `200`
  - `/a2a/health` is no longer `404` in local-docker runtime.
- Runtime/env contract updates:
  - local env contracts include `TEST_A2A_API_KEY=12345678`
  - local runtime auth contract includes `FILE_MCP_API_KEY_SECONDARY=12345678`
- Exact strict backend summary lines:
  - `137 passed, 1 skipped`
  - `21 passed`
  - `40 passed, 5 skipped`
  - `9 passed, 1 skipped`
- Exact strict UI summary lines:
  - `e2e: 16 passed (41.6s)`
  - `a11y: 6 passed (17.9s)`
- Evidence paths:
  - `working/W14B-04-FILE-MCP-A2A-ENABLE-AUTH-CONTRACT-REPORT-2026-03-01.md`
  - `/tmp/w14b04_file_ensure.log`
  - `/tmp/w14b04_file_health.json`
  - `/tmp/w14b04_file_mcp_tools.json`
  - `/tmp/w14b04_file_a2a_noauth.code`
  - `/tmp/w14b04_file_a2a_auth.code`
  - `/tmp/w14b04_file_ut.log`
  - `/tmp/w14b04_file_st.log`
  - `/tmp/w14b04_file_it.log`
  - `/tmp/w14b04_file_at.log`
  - `/tmp/w14b04_file_ui_lint.log`
  - `/tmp/w14b04_file_ui_typecheck.log`
  - `/tmp/w14b04_file_ui_e2e.log`
  - `/tmp/w14b04_file_ui_a11y.log`
- Current status: `COMPLETE VERIFIED`

## Latest W14A-03 Status (2026-03-01)

- Instruction file used:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14A-03-FILE-MCP-ROUTE-PFX-AND-TRACKER-RECONCILE-STRICT.md`
- Route-prefix contract adopted in active env files:
  - `TEST_API_BASE_PATH=/app/v1`
  - `TEST_MCP_BASE_PATH=/mcp`
  - `TEST_WEB_BASE_PATH=/`
  - `TEST_A2A_BASE_PATH=/a2a`
- Runtime route behavior:
  - canonical API: `/app/v1/*`
  - canonical MCP: `/mcp` (`GET /mcp/tools`)
  - compatibility aliases (explicit): `/health`, `/ready`, `/live`, and `/api/v1/health`
- Exact strict backend summary lines:
  - `133 passed, 1 skipped`
  - `21 passed`
  - `39 passed, 5 skipped`
  - `8 passed, 1 skipped`
- Exact strict UI summary lines (uncached):
  - `e2e: 16 passed (41.6s)`
  - `a11y: 6 passed (17.9s)`
- Evidence paths:
  - `working/W14A-03-FILE-MCP-ROUTE-PFX-AND-TRACKER-RECONCILE-REPORT-2026-03-01.md`
  - `working/w14a03/precheck-runtime-ensure.log`
  - `working/w14a03/precheck-health.json`
  - `working/w14a03/precheck-tools.json`
  - `working/w14a03/pytest-ut.log`
  - `working/w14a03/pytest-st.log`
  - `working/w14a03/pytest-it.log`
  - `working/w14a03/pytest-at.log`
  - `working/w14a03/health-canonical.json`
  - `working/w14a03/tools-canonical.json`
  - `working/w14a03/health-legacy-alias.json`
  - `working/w14a03/ui-lint.log`
  - `working/w14a03/ui-typecheck.log`
  - `working/w14a03/ui-e2e.log`
  - `working/w14a03/ui-a11y.log`
  - `working/w14a03/ui-last-run.json`
- Current status: `COMPLETE VERIFIED`

## Latest W11D Status (2026-02-28)

- Instruction files used:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W11D-04-FILE-MCP-LOCAL-DOCKER-IT-AT-STRICT.md`
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W11D-04A-FILE-MCP-CONTRACT-PUBLISH-CONSUMER-HANDOFF.md`
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W11D-04B-FILE-MCP-ROOT-SCOPE-CONTRACT-STRICT.md`
- Runtime env/controller env files used:
  - `tests/env-local-docker-server`
  - `tests/env-IT-local-docker`
  - `tests/env-AT-local-docker`
- Runtime image + hash:
  - `cloud-dog/file-mcp-server:latest`
  - `sha256:f1f25680c614fcfab73134ba5475cf2a5f03a4549aeb717308ba0caaa3858cca`
- Exact commands run:
  - `bash local-docker-server.sh --env tests/env-local-docker-server ensure`
  - `curl -fsS http://127.0.0.1:18090/health`
  - `curl -fsS http://127.0.0.1:18090/mcp/tools`
  - `./.venv/bin/python -m pytest tests/integration/ --env tests/env-IT-local-docker -q`
  - `./.venv/bin/python -m pytest tests/application/ --env tests/env-AT-local-docker -q`
  - W11D-04B strict sequence: `IT1.23`, `IT1.6`, `IT1.3`, `IT1.5`, `IT1.15`, `AT1.9`, restart, `IT1.6`
- Exact summary lines:
  - `39 passed, 5 skipped`
  - `8 passed, 1 skipped`
  - W11D-04B producer strict suites: all required suites passed
- Evidence report paths:
  - `working/W11D-P4-FILE-MCP-LOCAL-DOCKER-IT-AT-REPORT-2026-02-27.md`
  - `working/W11D-P4A-FILE-MCP-CONTRACT-PUBLISH-REPORT-2026-02-28.md`
  - `working/W11D-P4B-FILE-MCP-ROOT-SCOPE-CONTRACT-REPORT-2026-02-28.md`
  - Consumer closure evidence: `chat-client/working/W11D-P6B-FILE-MCP-CONSUMER-ALIGNMENT-RERUN-2026-02-28.md`
- Current status: `COMPLETE VERIFIED`

## Latest Verified Execution (2026-02-23)

| Tier | Command | Result |
|---|---|---|
| UT | `python3 -m pytest tests/unit/ --env tests/env-UT -v --tb=short` | `122 passed, 1 skipped, 0 failed` |
| ST | `python3 -m pytest tests/system/ --env tests/env-ST -v --tb=short` | `21 passed, 0 skipped, 0 failed` |
| IT | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a; python3 -m pytest tests/integration/ --env tests/env-IT -v --tb=short` | `29 passed, 16 skipped, 0 failed` |
| AT | `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a; python3 -m pytest tests/application/ --env tests/env-IT -v --tb=short` | `8 passed, 1 skipped, 0 failed` |
| Total | Tiered suite above | `180 passed, 18 skipped, 0 failed` |

## W11D-04A Local-Docker Contract Publish (2026-02-28)

| Item | Evidence |
|---|---|
| Instruction | `AGENT-INSTRUCTION-W11D-04A-FILE-MCP-CONTRACT-PUBLISH-CONSUMER-HANDOFF.md` |
| Control env | `tests/env-local-docker-server` (`LOCAL_DOCKER_SOURCE_ENV=tests/env-IT-local-docker`) |
| Runtime image target | `docker-compose.local.yml` -> running container image `cloud-dog/file-mcp-server:latest` |
| Runtime ensure command | `bash local-docker-server.sh --env tests/env-local-docker-server ensure` |
| Runtime ensure result | `ALREADY RUNNING with matching env` |
| Endpoint prechecks | `curl -fsS http://127.0.0.1:18090/health >/tmp/w11d04a_file_health.json` (`status=ok`) |
| MCP contract endpoint | `http://127.0.0.1:18090/mcp` |
| Auth contract | `Authorization: Bearer <FILE_MCP_API_KEY_PRIMARY>` |
| IT command | `./.venv/bin/python -m pytest tests/integration/ --env tests/env-IT-local-docker -q` -> `39 passed, 5 skipped` |
| AT command | `./.venv/bin/python -m pytest tests/application/ --env tests/env-AT-local-docker -q` -> `8 passed, 1 skipped` |
| Container/image identity | `file-mcp-local`, image `cloud-dog/file-mcp-server:latest`, image id `sha256:f1f25680c614fcfab73134ba5475cf2a5f03a4549aeb717308ba0caaa3858cca` |
| Report | `working/W11D-P4A-FILE-MCP-CONTRACT-PUBLISH-REPORT-2026-02-28.md` |

## W11D-04B Root/Scope Contract Strict (2026-02-28)

| Item | Evidence |
|---|---|
| Instruction | `AGENT-INSTRUCTION-W11D-04B-FILE-MCP-ROOT-SCOPE-CONTRACT-STRICT.md` |
| Runtime preconditions | `health=ok`, `FILE_MCP_ROOT=.`, `FILE_MCP_HTTP_PORT=18090`, `GET /mcp/tools -> TOOLS_OK 54` |
| Contract decode artifact | `/tmp/w11d04b_chat_path_contract.txt` (`PATH_CONTRACT_LINES 9`) |
| File-MCP strict suites | `IT1.23`, `IT1.6`, `IT1.3`, `IT1.5`, `IT1.15`, `AT1.9`, restart, `IT1.6` -> all passed |
| Consumer strict suites | `IT2.12`, `IT2.13`, `IT2.14`, `IT2.16`, `AT1.10`, `AT1.11` -> passed |
| Consumer blocker | Historical only (2026-02-28 initial run): `AT1.12` failed in chat-client with `500 INTERNAL_ERROR: ... missing MARKER line`; resolved by consumer rerun evidence (`chat-client/working/W11D-P6B-FILE-MCP-CONSUMER-ALIGNMENT-RERUN-2026-02-28.md`). |
| Error mapping proof | `/sessions/{id}/mcp/files/upload` returns `502` + code `UPSTREAM_ERROR` when upstream tool returns `isError=true` |
| Report | `working/W11D-P4B-FILE-MCP-ROOT-SCOPE-CONTRACT-REPORT-2026-02-28.md` |

## Consumer Handoff (chat-client)

- Runtime controller: `bash local-docker-server.sh --env tests/env-local-docker-server ensure`
- Health endpoint: `http://127.0.0.1:18090/health`
- MCP endpoint: `http://127.0.0.1:18090/mcp`
- Tools index compatibility endpoint: `http://127.0.0.1:18090/mcp/tools`
- MCP auth header: `Authorization: Bearer <FILE_MCP_API_KEY_PRIMARY>`
- A2A health endpoint: `http://127.0.0.1:18090/a2a/health`
- A2A strict local auth header: `Authorization: Bearer <TEST_A2A_API_KEY>`
- Consumer preflight: assert health endpoint `status=ok` before initiating MCP calls.

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
| `IT1.25_IntegrationA2AAuthContract` | `test_integration_a2a_auth_contract.py` | Integration A2A auth matrix (`401/401/200`) for `/a2a/health` |
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
| `AT1.10_ApplicationA2AAuthWorkflow` | `test_application_a2a_auth_workflow.py` | Application A2A auth flow using `TEST_A2A_API_KEY` |
| `AT1.2_ApplicationConversionEditWorkflow` | `test_application_conversion_edit_workflow.py` | Application conversion edit workflow |
| `AT1.3_ApplicationConversionStructuredWorkflow` | `test_application_conversion_structured_workflow.py` | Application conversion structured workflow |
| `AT1.4_ApplicationLifecycleWorkflow` | `test_application_lifecycle_workflow.py` | Application lifecycle workflow |
| `AT1.5_ApplicationMultifileTransactionWorkflow` | `test_application_multifile_transaction_workflow.py` | Application multifile transaction workflow |
| `AT1.6_ApplicationPreprodProfileChainHttp` | `test_application_preprod_profile_chain_http.py` | Application preprod profile chain http |
| `AT1.7_ApplicationSafeEditWorkflow` | `test_application_safe_edit_workflow.py` | Application safe edit workflow |
| `AT1.8_ApplicationSearchEditAuditWorkflow` | `test_application_search_edit_audit_workflow.py` | Application search edit audit workflow |
| `AT1.9_ApplicationSecurityBoundary` | `test_application_security_boundary.py` | Application security boundary |

## Web UI Traceability (`UI-P5-FILE-TST`)

### Scope

This section maps file-mcp Web UI requirements to `apps/file-mcp` Playwright coverage in `cloud-dog-ai-ui-monorepo`.

### Requirement -> Playwright Mapping

| Requirement ID | Spec ID | Playwright File | Coverage |
|---|---|---|---|
| `FR1.37`, `FR1.39` | `UI-E2E-01` | `apps/file-mcp/tests/e2e/auth.spec.ts` | API-key sign-in/sign-out flow, invalid-key rejection |
| `FR1.41` | `UI-E2E-02` | `apps/file-mcp/tests/e2e/dashboard.spec.ts` | Dashboard status cards and quick actions |
| `FR1.42` | `UI-E2E-03` | `apps/file-mcp/tests/e2e/file-browser.spec.ts` | Browse/create/edit/copy/move/delete flow |
| `FR1.42` | `UI-E2E-04` | `apps/file-mcp/tests/e2e/search.spec.ts` | Content/regex search and open-result handoff to browser |
| `FR1.43` | `UI-E2E-05` | `apps/file-mcp/tests/e2e/profiles.spec.ts` | Profile create/edit/test/delete workflow |
| `FR1.43` | `UI-E2E-06` | `apps/file-mcp/tests/e2e/audit-log.spec.ts` | Audit refresh/filter/export/pagination flow |
| `FR1.44` | `UI-E2E-07` | `apps/file-mcp/tests/e2e/settings.spec.ts` | Settings route contract: runtime-path fields visible and health-check action succeeds |
| `FR1.40` | `UI-E2E-08` | `apps/file-mcp/tests/e2e/routes.spec.ts` | Unknown route contract: wildcard route redirects to `/dashboard` |
| `FR1.44` | `UI-A11Y-01` | `apps/file-mcp/tests/a11y.spec.ts` | Automated WCAG 2.1 AA scans across authenticated dashboard/file-browser/search/storage-profiles/audit-log/settings routes |
| `FR1.38`, `FR1.40`, `FR1.45` | `UI-E2E-00` | `apps/file-mcp/tests/fixtures.ts`, `apps/file-mcp/playwright.config.ts` | Real runtime config injection, real backend boot via `server_control.sh --env tests/env-ST serve`, no mocked API path |

### Validation Commands (Strict)

Run from monorepo root:

```bash
npm run lint -- --filter=@cloud-dog/app-file-mcp
npm run typecheck -- --filter=@cloud-dog/app-file-mcp
npm run e2e -- --filter=@cloud-dog/app-file-mcp
npm run a11y -- --filter=@cloud-dog/app-file-mcp
```

Latest strict summary (2026-03-01):

- `npm run lint -- --filter=@cloud-dog/app-file-mcp` -> pass
- `npm run typecheck -- --filter=@cloud-dog/app-file-mcp` -> pass
- `npm run e2e -- --filter=@cloud-dog/app-file-mcp` -> `16 passed (41.6s)`
- `npm run a11y -- --filter=@cloud-dog/app-file-mcp` -> `6 passed (17.9s)`
- Evidence: `working/w14a03/ui-lint.log`, `working/w14a03/ui-typecheck.log`, `working/w14a03/ui-e2e.log`, `working/w14a03/ui-a11y.log`, `working/w14a03/ui-last-run.json`

### Gap Closeout Tracker (UI-P5-FILE-GAP)

Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W12D-FILE-MCP-UI-GAP-CLOSEOUT-STRICT.md`

| Gap ID | Description | Status | Required Evidence |
|---|---|---|---|
| `UI-GAP-01` | Add dedicated Playwright spec validating `/settings` interactions (`runtime-path` display + health-check action) end-to-end | COMPLETE VERIFIED (revalidated 2026-03-01) | `apps/file-mcp/tests/e2e/settings.spec.ts`; `working/w14a03/ui-e2e.log` (`settings route shows runtime paths and runs health check` passed) |
| `UI-GAP-02` | Add route-guard/navigation spec asserting unknown-route redirect contract (`* -> /dashboard`) | COMPLETE VERIFIED (revalidated 2026-03-01) | `apps/file-mcp/tests/e2e/routes.spec.ts`; `working/w14a03/ui-e2e.log` (`unknown route redirects to dashboard` passed) |
| `UI-GAP-03` | Expand a11y automation beyond dashboard to include file-browser/search/profiles/audit/settings routes | COMPLETE VERIFIED (revalidated 2026-03-01) | `apps/file-mcp/tests/a11y.spec.ts`; `working/w14a03/ui-a11y.log` (`6 passed`) |

Strict closeout pass criteria:

1. `npm run lint -- --filter=@cloud-dog/app-file-mcp` passes.
2. `npm run typecheck -- --filter=@cloud-dog/app-file-mcp` passes.
3. `npm run e2e -- --filter=@cloud-dog/app-file-mcp` passes including new gap specs.
4. `npm run a11y -- --filter=@cloud-dog/app-file-mcp` passes including expanded route coverage.
5. `cloud-dog-ai-ui-monorepo/apps/file-mcp/test-results/.last-run.json` reports passed status with no failed tests.

## W15B-02 Compliance Lockdown (2026-03-02)

- Scope: strict unresolved-placeholder fail-closed policy for active runtime config loading.
- Runtime loader policy:
  - `src/file_tools/config/adapter.py` now uses `unresolved_policy="strict"` (platform-supported strict mode).
  - Supporting config-load helper paths aligned:
    - `tests/remote_env_helpers.py`
    - `scripts/google_drive_setup.py`
- Deterministic runtime startup hardening:
  - `server_control.sh` now clears inherited `VAULT_*` only when the selected env file does not explicitly provide `VAULT_*` keys.
  - `src/file_mcp_server/main.py` start wait increased to 30s for strict startup paths.
- Mandatory verifier evidence:
  - `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-file-mcp-server-CONFIG.sh` -> pass (`14/14`).
  - `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-file-mcp-server-LOGGING.sh` -> pass (`12/12`).
  - `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-file-mcp-server-API-KIT.sh` -> pass (`17/17`).
- Mandatory strict tier evidence:
  - `python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q` -> `21 passed`.
  - `python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q` -> `34 passed, 11 skipped`.
  - `python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q` -> `9 passed, 1 skipped`.
- Local-docker remote-backend policy:
  - Local-docker envs explicitly set `FILE_MCP_STRICT_REMOTE_TESTS=0` and `FILE_MCP_RUN_REMOTE_MATRIX_TESTS=0`.
  - Live remote backend IT test (`IT1.14`) is explicitly gated by `FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS` unless strict remote mode is enabled.
