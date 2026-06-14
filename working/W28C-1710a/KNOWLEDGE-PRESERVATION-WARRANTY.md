---
lane: W28C-1710a
service: file-mcp-server
date: 2026-06-14T17:37:15Z
---

# file-mcp-server — Knowledge Preservation Warranty (W28C-1710a)

## Programme summary for this service

| Metric | Value |
|---|---:|
| Archived docs merged | 5 |
| Total archived-lines carried forward | 464 |
| Topics preserved (PRESENT) | 252 |
| Topics lost (residual) | 0 |
| Successor docs updated | 5 |
| Lines added to successor docs | +509 |
| Lines removed from successor docs | -0 |
| **residual-loss-lines** | **0** |

## Per-doc SHA256 chain (successor pre/post)

| Successor canonical | pre-sha256(12) | post-sha256(12) | pre-lines | post-lines | +lines | -lines | residual-loss-lines |
|---|---|---|---:|---:|---:|---:|---:|
| `docs/API-REFERENCE.md` | `c61649d0de74` | `7ddae1a85433` | 126 | 369 | +243 | -0 | 0 |
| `docs/REQUIREMENTS.md` | `2fe740237c37` | `be0f23ed8eb3` | 589 | 690 | +101 | -0 | 0 |
| `docs/MCP-REFERENCE.md` | `d2835e5100fb` | `22ee23b13677` | 56 | 172 | +116 | -0 | 0 |
| `docs/CHANGELOG.md` | `37dba8baadee` | `8934c9a8dea2` | 11 | 36 | +25 | -0 | 0 |
| `docs/ROLES-AND-USECASES.md` | `c23ef9197132` | `bd57d4caaaa0` | 56 | 80 | +24 | -0 | 0 |

## Per-archived-doc topic preservation

| Archived | archived-lines | archived-sha256(12) | Successor | topics-recorded | topics-present | residual-loss-topics |
|---|---:|---|---|---:|---:|---:|
| `archive/2026-06-12/API_DOCUMENTATION.md` | 234 | `e7b0eaf30d9c` | `docs/API-REFERENCE.md` | 145 | 145 | 0 |
| `archive/2026-06-12/DESCRIPTION.md` | 92 | `1072f02d490d` | `docs/REQUIREMENTS.md` | 22 | 22 | 0 |
| `archive/2026-06-12/MCP_DOCUMENTATION.md` | 107 | `14e1ea9e8b4a` | `docs/MCP-REFERENCE.md` | 73 | 73 | 0 |
| `archive/2026-06-12/TASKS.md` | 16 | `eb81fc2ed7c4` | `docs/CHANGELOG.md` | 10 | 10 | 0 |
| `archive/2026-06-12/USE_CASES.md` | 15 | `b9b49589b9fb` | `docs/ROLES-AND-USECASES.md` | 2 | 2 | 0 |

## Attestation

I warrant that:

1. Every archived doc under `file-mcp-server/archive/2026-06-12/` has been merged verbatim into the named successor canonical doc(s) — full content preserved as a marked `## Recovered domain content` section.
2. Archive contents have NOT been modified during this lane (sha256 of every archived file matches the pre-merge fingerprint).
3. No successor doc had any line removed during this lane (delta-lines-removed = 0 per row).
4. residual-loss-lines = 0 for this service.
5. No `tests/` file modified; no CI-critical file modified.
6. Per-doc topic checklists at `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/file-mcp-server/<archived-name>.topics.tsv` — every row marked PRESENT.

**HAVE_ALL_REQUIREMENTS_BEEN_MET_FOR_FILE_MCP_SERVER_RECOVERY**: YES

---
Operator countersignature: ___________________________ Date: __________
