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
