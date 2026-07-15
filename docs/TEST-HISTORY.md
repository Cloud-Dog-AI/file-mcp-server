---
template-id: T-TSH
template-version: 1.0
applies-to: docs/TEST-HISTORY.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-07-15T06:29:27Z
doc-git-commit: 2fc3bb8f7dfd5d99ab4cc2b99aa95055465729e4
doc-git-branch: main
doc-source-shas: []
doc-age-policy: indefinite
doc-conformance-stamp: 2026-07-15T06:29:27Z
---

# file-mcp-server - TEST-HISTORY

> **Template version:** T-TSH v1.0. Only complete-provenance runs are canonical.

## Runs (most recent first)

### 2026-07-14T14:04:18.739Z — W28E-1882
- Commit: `2285536dc3e19489a133bd69509db2834695685b` (main)
- Runtime: N/A (Node/Playwright)
- Environment: `deployed preprod; approved runtime/Vault credentials; service E2E_BASE_URL`
- Command: `bash /opt/iac/Development/cloud-dog-ai/tmp/W28E-1882/run-filemcp-e2e.sh FINAL`
- Evidence: `W28E-1882-FINAL-PROOF-R2:working/evidence/W28E-1882/current/raw/file-mcp/file-mcp-server.FINAL.junit.xml`
- Totals: 165 / P 165 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-14T17:55:26Z - W28R-3013 traceability correction
- Timestamp source: `date -u +%Y-%m-%dT%H:%M:%SZ` captured `2026-07-14T17:55:26Z` (epoch `1784051726`).
- Commit: `2fc3bb8f7dfd5d99ab4cc2b99aa95055465729e4` (`origin/main` documentation review baseline)
- Runtime: N/A (documentation-only evidence audit; no test run)
- Lane: `W28R-3013` seven-day traceability correction
- Environment: NOT IMPORTED
- Command: N/A (documentation audit only)
- Evidence: `docs/TEST-CANDIDATE-DISPOSITION.tsv`; immutable W28R-3013 R2/R3 tags and remote branch audit
- Totals: 0 / P 0 / F 0 / E 0 / S 0 canonical imported runs
- Delta: removed R4 CPython and R3 browser imports because literal commands are absent and the cited R4 remote evidence/tags do not exist
- Runtime separation: CPython 3.12 NOT RUN; CPython 3.13 R2/R3/R4 totals NOT IMPORTED; Node/Playwright R2/R3/W28E-1882 totals NOT IMPORTED.
- Adverse evidence preserved: R2 IT 43P/7E/1S; AT 25P/4F/1S; Docker IT 9P/1F; deployed browser 97P/8F/10S/50 not run.

### 2026-06-24T07:35:00+00:00
- Commit: `9366506b497265613fd0775d207910d3b1b695bb` (main)
- Totals: 21 / P 21 / F 0 / S 0
- Delta: Stream-C WebUI proof expanded to 18 screenshots, 12 alias rows, and 16 axe page checks.

### 2026-06-17T11:09:42.839473+00:00
- Commit: `cd8e9d759a1c30b5ea7a1e4b75b3389232c6658e` (W28C-1714-100pct-fix)
- Totals: 8 / P 8 / F 0 / S 0
- Delta: new-fails 0 | newly-green 59

### 2026-06-13T10:59:11.209949+00:00
- Commit: `d893dd83bd865d6699918b9ceecd2ae53e1f873e` (main)
- Totals: 124 / P 64 / F 59 / S 1
- Delta: new-fails 59 | newly-green 35

### 2026-06-13T10:18:36.105689+00:00
- Commit: `d893dd83bd865d6699918b9ceecd2ae53e1f873e` (main)
- Totals: 98 / P 63 / F 35 / S 0
- Delta: new-fails 35 | newly-green 0

### 2026-06-12T12:00:00Z
- Commit: `708278bca73b1a0cbdb03f1b108122d55cfd259e` (main)
- Totals: N / P n / F n / S n
- Delta: new-fails 0 | newly-green 0
