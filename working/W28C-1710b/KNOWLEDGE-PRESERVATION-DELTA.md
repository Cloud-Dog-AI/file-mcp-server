---
lane: W28C-1710b
service: file-mcp-server
date: 2026-06-14T18:01:23Z
---

# file-mcp-server — W28C-1710b Knowledge Preservation Delta

## Pre/post SHA256 chain (per PS-REQ-TEST-TRACE §A3)

| Doc | pre-1710b-sha256(12) | post-1710b-sha256(12) | lines-added | lines-removed | every-recovered-topic-still-present |
|---|---|---|---:|---:|---|
| `docs/REQUIREMENTS.md` | `be0f23ed8eb3` | `950b0b6842b0` | ADDITIVE | 0 | YES |
| `docs/ROLES-AND-USECASES.md` | `bd57d4caaaa0` | `ab6d394d021f` | ADDITIVE | 0 | YES |
| `docs/TESTS.md` | `74b24c01119c` | `ac074de8e6e7` | ADDITIVE | 0 | YES |

## New rows added by W28C-1710b

- 12 CS-NNN baseline rows (anon-denied / wrong-role-denied / missing-param-error per surface in {api, mcp, a2a, webui})
- PS-REQ-TEST-TRACE schema completion block (default schema applied to all existing FR-NNN rows)
- UC cross-surface schema block (defaults applied; per-UC operator review in W28C-1711)
- T-TST v1.1 10-col catalogue schema + 8 consolidation rules in TESTS.md

## Topics-lost = 0 attestation

All additions in this lane are purely additive `## W28C-1710b design-delta additions` sections appended to the post-1710a successor canonical docs. NO content from W28C-1710a recovery removed. NO archive content modified. NO tests/ file modified.

**topics-lost: 0** · **lines-removed: 0** · **W28C-1710a recovered topics still PRESENT: YES**
