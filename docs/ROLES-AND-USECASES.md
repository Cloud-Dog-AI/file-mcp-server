---
template-id: T-RUC
template-version: 1.0
applies-to: docs/ROLES-AND-USECASES.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-12
doc-git-commit: 708278bca73b1a0cbdb03f1b108122d55cfd259e
doc-git-branch: main
doc-source-shas: []
doc-age-policy: indefinite
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# file-mcp-server — ROLES-AND-USECASES

> **Template version:** T-RUC v1.0

## 1. Roles
Canonical roles from PS-83-canonical-role-catalog.md plus any project-local extensions.

| Role | From | Notes |
|---|---|---|
| admin | platform | full access |
| read-write | platform | data write |
| read-only | platform | data read |
| <project-role> | local | <purpose> |

## 2. Personas
| Persona | Description | Roles |
|---|---|---|

## 3. Use cases
**You MUST include:** UC-001…UC-NNN. One row per persona+goal pair.

| UC ID | Persona | Goal | Surface (REST/MCP/A2A/WEBUI) | Requirements | Tests |
|---|---|---|---|---|---|

## 4. Negative use cases (admin/security)
Tests for refused/forbidden flows — required to prove RBAC.

| UC ID | Persona | Attempted | Expected | Test |
|---|---|---|---|---|

## 5. Cross-references
- [REQUIREMENTS.md](REQUIREMENTS.md)
- [TESTS.md](TESTS.md)
- PS-82-access-control-session-test-matrix.md
- PS-83-canonical-role-catalog.md

## 6. Project-specific notes



<!-- W28C-1710a recovery: full content from archive/2026-06-12/USE_CASES.md (archived sha256=b9b49589b9fb, 15 lines) -->

## Recovered domain content — `archive/2026-06-12/USE_CASES.md` (15 lines)

_This section carries forward the full content of the archived predecessor doc verbatim. Topic checklist + SHA256 chain in `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/file-mcp-server/USE_CASES.md.topics.tsv`. Archive contents are unchanged (sha256 stable)._

# File MCP Use Cases

## UC-CFG-01 New File Storage Profile For A Project Folder

1. Provision a new file profile scoped to a dedicated project subfolder.
2. Confirm the profile exposes only its configured scope roots.
3. Create a dated subfolder and upload markdown and PDF content.
4. Read, edit, rename, search, and delete those files using the profile.
5. Update the profile to adjust limits or storage behaviour.
6. Re-run file operations and verify the new policy is enforced.
7. Delete the profile and confirm it can no longer be selected for later operations.

Current status:
- Dynamic profile lifecycle exists.
- Generic user/group/API-key CRUD and WebUI parity are not yet delivered.
