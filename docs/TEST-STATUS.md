---
template-id: T-TSS
template-version: 1.0
project: file-mcp
doc-last-updated: 2026-07-14T14:04:18.739Z
doc-git-commit: 2285536dc3e19489a133bd69509db2834695685b
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-14T14:04:18.739Z
---

# file-mcp — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-07-14T14:04:18.739Z
- **Commit:** `2285536dc3e19489a133bd69509db2834695685b` (`main`)
- **Runtime:** N/A (Node/Playwright)
- **Lane:** `W28E-1882`
- **Environment:** `deployed preprod; approved runtime/Vault credentials; service E2E_BASE_URL`
- **Command:** `bash /opt/iac/Development/cloud-dog-ai/tmp/W28E-1882/run-filemcp-e2e.sh FINAL`
- **Evidence:** `W28E-1882-FINAL-PROOF-R2:working/evidence/W28E-1882/current/raw/file-mcp/file-mcp-server.FINAL.junit.xml`
- **Totals:** 165 tests | 165 passed | 0 failed | 0 errors | 0 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `W28A-A10-about-profile-contract.spec.ts::W28A-#38 file-mcp about/profile contract › AboutDialog exposes the 5 contract data-testid attributes with correct values` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `W28A-A10-about-profile-contract.spec.ts::W28A-#38 file-mcp about/profile contract › ProfileDialog exposes the 7 contract data-testid attributes via UserMenu.onProfile` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `W28A-A10-about-profile-contract.spec.ts::W28A-#38 file-mcp about/profile contract › Settings page renders without bespoke fallback (PS-73 SettingsPanel surface)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `W28A-A14-preprod-about-profile-contract.spec.ts::W28A-#A14 file-mcp preprod about/profile contract › AboutDialog exposes the 5 contract data-testid attributes (preprod)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `W28A-A14-preprod-about-profile-contract.spec.ts::W28A-#A14 file-mcp preprod about/profile contract › ProfileDialog exposes the 7 contract data-testid attributes via UserMenu (preprod)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `W28A-A14-preprod-about-profile-contract.spec.ts::W28A-#A14 file-mcp preprod about/profile contract › Settings page renders SettingsPanel surface (preprod)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y a2a-console has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y admin-api-keys has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y admin-groups has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y admin-rbac has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y admin-roles has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y admin-users has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y api-docs has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y audit-log has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y dashboard has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y file-browser has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y google-drive-settings has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y jobs has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y mcp-console has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y search has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y settings has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `a11y.spec.ts::@a11y storage-profiles has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 about, profile, and settings expose exact platform contract content` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 deterministic search term error opens the seeded file result` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 file browser has folder, metadata, preview, grid, and bulk UX depth` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 identity and RBAC pages expose CRUD, relation, and guarded binding UX` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 jobs page asserts details, action affordances, export, or explicit empty state` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-117-deep-ux.spec.ts::W28A-117 storage profile test connection exposes status, reason, and toast result` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-119A-rendered-assertions.spec.ts::W28A-119A file browser renders type icons, metadata, tree expansion, and selected preview` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-119A-rendered-assertions.spec.ts::W28A-119A search term error renders deterministic preview and opens the result` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/W28A-119A-rendered-assertions.spec.ts::W28A-119A storage profile connection test renders an inline row status` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/admin-identity.spec.ts::admin identity pages load (users, groups, api keys)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/audit-log.spec.ts::view, filter and export audit log` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/auth.spec.ts::api-key sign-in and sign-out works` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/auth.spec.ts::invalid credentials show an error` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/dashboard.spec.ts::dashboard shows health, backend and quick actions` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/file-browser.spec.ts::browse, create, edit, copy, move and delete file` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/google-drive-connected-card.spec.ts::W28C-433 UX verification › google-drive-settings requires re-authorisation when live health is auth_failed` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/google-drive-connected-card.spec.ts::W28C-433 UX verification › storage-profiles hides example-* templates by default; toggle reveals them` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/google-drive-settings.spec.ts::google drive settings page loads profile defaults` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/mcp-console-gdrive.spec.ts::MCP Console storage profile execution › reports Google re-authorisation and completes local write → read → delete` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-002 health and version return 200` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-003 runtime-config + main assets + index load without 404/500` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-004 login page renders the shared login form (no blank/pageerror)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-005 login alias /ui/login resolves without 404/5xx` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-006 bad credentials fail visibly without crashing` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-007 valid login materialises the principal via /auth/me` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-008 authenticated shell renders top bar, nav and account menu` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-009 canonical common pages render via hard navigation (no blank/pageerror)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-010 service pages render via hard navigation — the crash-class guard` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-011 anonymous + wrong-target access does not leak protected content` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-012 browser cleanliness across the full journey` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: file-mcp-server target-service smoke › PDS-013 logout returns to the login gate` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::browse button navigates to file browser with profile` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::configure button opens edit or google drive settings` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::create, edit, test and delete storage profile` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::jobs page shows full job ID with copy button` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::profile detail panel shows for selected profile` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/profiles.spec.ts::storage profiles page shows deterministic status` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/routes.spec.ts::canonical routes and aliases resolve deterministically` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/routes.spec.ts::unknown route renders not found` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/search.spec.ts::search by content and open result` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/settings.spec.ts::settings route renders the effective-config panel and health card` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/storage-backends-matrix.spec.ts::Storage backends matrix (W28C-433 + smoke) › file-browser loads for profile ftp` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/storage-backends-matrix.spec.ts::Storage backends matrix (W28C-433 + smoke) › file-browser loads for profile google_drive` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/storage-backends-matrix.spec.ts::Storage backends matrix (W28C-433 + smoke) › file-browser loads for profile s3` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/storage-backends-matrix.spec.ts::Storage backends matrix (W28C-433 + smoke) › remote-backend profiles show their truthful live status in Storage Profiles list` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/stream-c-proof.spec.ts::stream-c canonical pages produce browser proof` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/stream-c-proof.spec.ts::stream-c legacy aliases return 308 to canonical routes` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T1 Dashboard — HealthWidgets visible (API, MCP, A2A traffic lights)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T10 FileBrowser — Column picker dropdown works` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T11 FileBrowser — RelativeTime appears on date columns` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T12 FileBrowser — EntityDialog opens on Add File click` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T13 StorageProfiles — EntityDialog opens on Add Profile click` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T14 StorageProfiles — DataTable has sort, page jump, multi-select` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T15 Admin > Users route exists` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T16 Admin > Groups route exists` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T17 Admin > API Keys route exists` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T18 API Docs — page loads and Swagger iframe visible` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T19 Jobs — page loads with jobs list or empty state` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T2 Dashboard — MetricCards visible (file count, storage, profiles)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T20 MCP Console — ToolBrowser visible and searchable` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T20b MCP Console — execute write_file shows JsonBlock response` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T20c A2A Console — send shows JsonBlock response` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T21 Session timeout — NOT shown on login page` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T22 Session timeout — MM:SS countdown visible when authenticated` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T23 AuditLog — DataTable has sort, page jump, RelativeTime` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T24 Navigation — new pages are accessible from sidebar` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T25 No raw JSON — spot-check key pages` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T3 Dashboard — QuickActionBar buttons navigate` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T4 Dashboard — No raw JSON blocks` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T5 Dashboard — ResourceMetrics shows real data` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T6 FileBrowser — DataTable has page jump input` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T7 FileBrowser — DataTable sort arrows on column click` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T8 FileBrowser — DataTable multi-select checkboxes visible` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/ui-review2.spec.ts::T9 FileBrowser — Bulk action toolbar appears on select` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::A: 5 lifecycle states visible` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::B: 12 columns in order` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::C: badge colours` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::D: detail dialog 7 tabs + controls + Escape` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::E1: admin sees all jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::F1: exact Job ID search` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::F2: status filter` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::F4: pagination` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::F6: bulk Cancel confirm` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-jobs-compliance.spec.ts::G: cross-page smoke` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-rbac-e2e8.spec.ts::RBAC E2-E8 › E1: admin sees all jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-rbac-e2e8.spec.ts::RBAC E2-E8 › E2: non-admin sees jobs page` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-rbac-e2e8.spec.ts::RBAC E2-E8 › E4: non-admin bulk delete hidden` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-rbac-e2e8.spec.ts::RBAC E2-E8 › E5: non-admin bulk cancel own job` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r2-rbac-e2e8.spec.ts::RBAC E2-E8 › E8: admin bulk delete with confirmation` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › A: 5 lifecycle states visible on /jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › B1: 12 columns in PS-76 exact order` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › B2: checkbox column` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › B3: column picker` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › B4: default sort Created desc` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › B5: clickable non-empty Job IDs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › C1: succeeded green` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › C2: failed red` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › C3: retry_wait yellow` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › C4: cancelled secondary` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › C5: running neutral` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › D1: detail dialog 7 tabs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › D2: Copy/Retry/Cancel/Delete controls` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › D3: Escape closes dialog` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E1: admin sees all jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E2: non-admin sees only own jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E3: non-admin direct URL to another actor job shows inline 403 or filtered` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E4: non-admin bulk delete is hidden` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E5: non-admin bulk cancel own job succeeds` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E6: non-admin bulk cancel another actor job shows inline 403` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E7: non-admin bulk retry own failed job succeeds` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › E8: admin bulk delete across actors with confirmation` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F1: exact Job ID search` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F2: status filter` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F3: Total Records` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F4: Page X of Y with Prev/Next` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F5: page size 10/25/50/100` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F6: bulk Cancel confirm` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F7: bulk Retry confirm` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › F8: bulk Delete confirm (admin)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-687-r3-jobs-compliance.spec.ts::W28A-687-R3 Jobs PS-76 v2 Compliance › G: cross-page smoke clean` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.1 A2A skill list count equals live agent card and is scrollable` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.1 MCP tool list count equals live tools/list and is scrollable` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.2 tool and skill selection populate valid request templates` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.3 API key field is masked with password override and no plain key leak` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.4 and T.1.5 submit and result/meta are directly connected` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.1.7 docs links route to the PS-74 docs page` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.2.1 and T.1.6 safe MCP list_dir returns real result and PS-40 ids` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.2.2 and T.1.8 safe A2A task returns final result and live events` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.2.3 async managed tool returns job id and links to Jobs page` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.2.4 RBAC denial surfaces inline for unbound profile` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-769-ps72-conformance.spec.ts::W28A-769 PS-72 conformance › T.2.5 API-key override succeeds for MCP and A2A` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/secret-masking-capture.spec.ts::capture 5 masked secret keys` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › 3.3 random sample of 10 keys present with source badge` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › 3.4 reveal requires explicit admin action and calls the reveal endpoint` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › 3.6 JSON explorer expand-all and collapse-all work` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A1+3.2 every effective-config key renders (incl. config-only additions); count matches` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A2+3.4 secret keys are masked by default (incl. config-only profile secrets)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A3 every rendered leaf carries a valid source badge` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A4+3.7 every server tab is non-empty` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A5+3.5 page search highlights matching nodes` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A6 reveal toggle is present for admin` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `e2e/w28a-799/settings/settings-conformance.spec.ts::W28A-799 PS-73 v2 Settings conformance › A7+3.1 page loads with the PS-81 JsonExplorer (no 4xx)` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |
| `smoke/all-pages.spec.ts::all main navigation routes load` | UNCLASSIFIED | pass | 2026-07-14 | `2285536d` | |

## 3. Failures (detail)

_None._
