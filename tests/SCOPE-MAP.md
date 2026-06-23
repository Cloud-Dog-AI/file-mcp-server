---
template-id: T-SCM
template-version: 1.0
applies-to: tests/SCOPE-MAP.md
project: file-mcp-server
doc-last-updated: 2026-06-23T14:02:08Z
doc-git-commit: 157f34c69faf321586cdb0ec962c0f4a9d1a3f1b
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-06-23T14:02:08Z
---

# file-mcp-server — Test scope map

> **Template version:** T-SCM v1.0 — required by PS-REQ-TEST-TRACE §5. Maps `src/**` module groups to
> the requirements they implement and the scoped test IDs that exercise them, for scoped CI runs.
> Refreshed in W28E-1802A alongside the semantic REQ binding.

## Mapping

| Source glob | Requirement(s) | Test IDs |
|---|---|---|
| `src/file_tools/tools/**` | `FR-001` | `UT1.24_ToolsRegistry`, `UT1.36_ParamAliasFallback` |
| `src/file_tools/io/**` | `FR-018`, `FR-011` | `UT1.10_Filesystem`, `UT1.17_Posix`, `ST1.11_SystemReadPartialRanges` |
| `src/file_tools/edit/**` | `FR-004`, `FR-005` | `UT1.7_EditStructured`, `UT1.20_Sedlike`, `ST1.15_SystemStructuredRollbackContract` |
| `src/file_tools/validate/**` | `FR-006` | `UT1.25_Validate`, `ST1.16_SystemValidateFileTool` |
| `src/file_tools/search/**` | `FR-019`, `FR-025` | `UT1.19_Search`, `IT1.16_IntegrationSearchHttp`, `ST1.18_TimeBasedSearch` |
| `src/file_tools/convert/**` | `FR-008` | `UT1.5_Convert`, `ST1.3_SystemConversionMatrix` |
| `src/file_tools/diff/**` | `FR-003`, `FR-002` | `UT1.6_Diff`, `IT1.3_IntegrationBase64FileOps`, `IT1.5_IntegrationDiffFilesHttp` |
| `src/file_tools/scope/**` | `FR-024`, `CS-001`–`CS-016` | `UT1.18_ScopePolicy`, `UT1.35_FlatRoleLogin`, `AT1.9_ApplicationSecurityBoundary` |
| `src/file_tools/storage/**` | `FR-012`, `FR-021` | `IT1.14_IntegrationRemoteStorageBackendsHttp`, `UT1.14_GoogleDriveStorage`, `UT1.26_WebdavStorage` |
| `src/file_tools/audit/**` | `FR-022`, `NF-003`, `CFG-12` | `UT1.2_Audit`, `UT_AuditLogFormat`, `ST1.1_SystemAuditIntegrity`, `QT_LoggingCompliance` |
| `src/file_tools/config/**`, `src/file_tools/adapters/**` | `FR-013`, `NF-001`, `NF-002` | `UT1.4_ConfigLoader`, `QT_PackageCompliance`, `QT26_SecretsSeparation`, `QT_VaultConfigContract` |
| `src/file_mcp_server/auth.py`, `idam_seam.py`, `web_flat_roles.py` | `FR-017`, `FR-024`, `CS-005`–`CS-012` | `UT1.3_Auth`, `UT1.35_FlatRoleLogin`, `IT1.25_IntegrationA2AAuthContract`, `IT1_30_AuthStatusProbe` |
| `src/file_mcp_server/server_runtime.py`, `mcp_api_kit_layer.py`, `route_guards.py` | `FR-007`, `FR-016`, `FR-023` | `UT1.1_ApiKitContract`, `IT1.12_IntegrationMultiProfileRoutingHttp`, `IT1.23_ServerHttpIntegration` |
| `src/file_mcp_server/admin_identity.py`, `google_drive_admin.py` | `CFG-01`–`CFG-11`, `FR-015` | `AT_ProfileCRUD`, `AT1.11_DynamicProfileCRUDLifecycle`, `IT1.26_IntegrationConfigCrudIdentityWorkflow`, `AT1.12_GoogleDriveOauthLive` |
| `src/file_mcp_server/endpoint_health.py` | `FR-014`, `FR-020` | `UT1.9_EndpointHealth`, `ST1.7_SystemEndpointRestartThreshold` |
| `src/file_mcp_server/jobs_runtime.py` | `FR-027`, `FR-029` | `IT1.24_JobsManagedFileOps`, `tests/integration/** cluster` |
| `src/file_mcp_server/lifecycle.py` | `FR-028` | `UT1.15_Lifecycle`, `tests/system/** cluster` |
| `src/file_mcp_server` observability / operational logging | `FR-022` | `UT1.16_Observability` |
| WebUI app `@cloud-dog/app-file-mcp` (monorepo) | `FR-012`, `FR-016`, `FR-023`, `FR-024`, FR1.37–FR1.47 | `AT_WEBUI_EndToEnd`, `AT1.13_ApplicationWebUiAdmin` (Stream-C Playwright) |

## Cross-references

- Platform standard: PS-REQ-TEST-TRACE v1.0 §5
- Tier policy: standards/TEST-POLICY-SCOPED.md
- Requirement set: [../docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md) · Coverage: [../docs/REQ-COVERAGE.md](../docs/REQ-COVERAGE.md)
