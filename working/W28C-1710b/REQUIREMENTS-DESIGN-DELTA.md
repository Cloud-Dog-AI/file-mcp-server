---
lane: W28C-1710b
service: file-mcp-server
date: 2026-06-14T18:01:23Z
---

# file-mcp-server — REQUIREMENTS Design Delta (W28C-1710b)

## 100% recovery precondition (W28C-1710a)

- W28C-1710a closed YES with programme `residual-loss-lines = 0`.
- Pre-1710b SHAs captured below.

## Existing requirements inventory (post-1710a)

| Doc | FR-NNN | CS-NNN | UC-NNN | Legacy R-NNN |
|---|---:|---:|---:|---:|
| REQUIREMENTS.md | 0 | 4 | 0 | 0 |
| ROLES-AND-USECASES.md | 0 | 0 | 0 | 0 |

## Service surface set (operator-editable)

`file-mcp-server` declares surfaces: **api, mcp, a2a, webui**.

## Required schema completion for existing FR-NNN rows (per PS-REQ-TEST-TRACE §2 + §3)

Every existing FR-NNN (or legacy R-NNN) row must, per the binding standard, declare:

- `surface:` — one or more of `api`, `mcp`, `a2a`, `webui`, `cli`, `internal`
- `priority:` — `must` / `should` / `may`
- `since:` — git short-sha when first added
- `last-verified:` — `<git-sha> <ISO-date>`
- `tests:` — list of `<test-id>` (empty allowed pre-1711)
- `crud:` — one of `C` / `R` / `U` / `D` / `CRUD` / `CR` / `RU` / `N/A`

This delta proposes adding a per-FR schema annotation block above each existing FR row. **The 1710b lane applies a programme-wide `## PS-REQ-TEST-TRACE schema completion` section to `docs/REQUIREMENTS.md`** that declares the default values pending operator per-row review.

## Proposed CS-NNN baseline (per PS-REQ-TEST-TRACE §2 + §3.4)

Every project MUST have CS-NNN rows for `anon-denied`, `wrong-role-denied`, `missing-param-error` per surface present. Proposed additions:

| CS-NNN | Scenario | Surfaces | Expected | Roles |
|---|---|---|---|---|
| `CS-005` | anon-denied on `api` surface | `api` | `401` | `anon` |
| `CS-006` | anon-denied on `mcp` surface | `mcp` | `401` | `anon` |
| `CS-007` | anon-denied on `a2a` surface | `a2a` | `401` | `anon` |
| `CS-008` | anon-denied on `webui` surface | `webui` | `401` | `anon` |
| `CS-009` | wrong-role-denied on `api` surface | `api` | `403` | `read-only` |
| `CS-010` | wrong-role-denied on `mcp` surface | `mcp` | `403` | `read-only` |
| `CS-011` | wrong-role-denied on `a2a` surface | `a2a` | `403` | `read-only` |
| `CS-012` | wrong-role-denied on `webui` surface | `webui` | `403` | `read-only` |
| `CS-013` | missing-param-error on `api` surface | `api` | `422` | `*` |
| `CS-014` | missing-param-error on `mcp` surface | `mcp` | `422` | `*` |
| `CS-015` | missing-param-error on `a2a` surface | `a2a` | `422` | `*` |
| `CS-016` | missing-param-error on `webui` surface | `webui` | `422` | `*` |

## Proposed UC cross-surface mappings (per T-RUC v1.1)

Existing UC-NNN: 0. For services where UC-NNN spans multiple surfaces, the cross-surface map declares `surfaces: [api, mcp, webui]` shape.

Detailed UC-by-UC operator-review pass deferred to per-FR mapping in W28C-1711. This delta declares the schema requirement only.

## Consolidation plan (per W28C-1711 binding rules)

`consolidation-plan.tsv` proposes 1 primary test per FR-NNN; variants via `pytest.parametrize`; common scenarios extracted to `tests/helpers/`. Cross-surface FRs share parametrized test files.

## Pre-1710b SHA chain (A3)

- `docs/REQUIREMENTS.md` pre-sha256: `be0f23ed8eb3`
- `docs/ROLES-AND-USECASES.md` pre-sha256: `bd57d4caaaa0`
- `docs/TESTS.md` pre-sha256: `74b24c01119c`

