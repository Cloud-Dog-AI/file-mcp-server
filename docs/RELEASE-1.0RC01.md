# file-mcp-server 1.0RC01 Release Notes

Release lane: `W28E-1802C`  
Date: `2026-06-24`

## Source And Runtime Identity

- Service source commit for deployed WebUI bundle: `9366506b497265613fd0775d207910d3b1b695bb`
- UI proof inventory commit: `cae462011e10768bc01ca654a7b5e2c9cc749548`
- Preprod URL: `https://filemcpserver0.cloud-dog.net`
- Preprod image id: `sha256:8d291fcedf7eb2710e8fe3d7e87935b82442a0f9ba1d08d5a660ee5c9b9c8032`
- Registry digest: `sha256:c5d1fca676fa0497507b2c9a007550c4c613d2c77694380b18951c7b1a6cee68`

## WebUI Closure

- Canonical WebUI routes now use `/developer/*`, `/system/*`, and `/admin/*` paths.
- Legacy aliases return HTTP `308` to canonical paths, preserving query strings.
- Unknown root paths no longer fall back to the SPA shell.
- Browser proof covers login/session handling, dashboard, file browser, storage profiles, search, audit log, users, groups, API keys, roles, RBAC, Google Drive settings, API docs, MCP console, A2A console, jobs, settings, and about.
- Google Drive settings proof preserved the existing W28M-1603A-R2 auth context.

## Verification

- Local WebUI pack: `15 passed`.
- Local Docker Stream-C proof: `2 passed`.
- Preprod Stream-C browser proof: `2 passed`, with 18 canonical screenshot rows and 12 alias rows all PASS.
- Preprod smoke/routes/a11y: `19 passed`, including 16 axe WCAG2AA page checks.
- Sibling Chromium smoke: target plus four sentinels PASS with zero unexpected console errors, zero failed assets, and zero failed critical requests.
- Warranty gate: Section A 74 PASS, Section B 29 PASS, Section C 160 PASS.

Evidence root: `cloud-dog-ai-platform-standards/working/evidence/W28E-1802C/current/`.
