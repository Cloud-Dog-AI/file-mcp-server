---
template-id: T-TSS
template-version: 1.0
project: file-mcp-server
doc-last-updated: 2026-07-14
doc-git-commit: 2fc3bb8f7dfd5d99ab4cc2b99aa95055465729e4
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-14T17:55:26Z
---

# file-mcp-server - TEST-STATUS

> **Template version:** T-TSS v1.0. Canonical results require original UTC time, tested commit, literal foreground command, exact environment/configuration, runtime, totals, and immutable raw evidence together.

## 1. Latest run

- **Run timestamp:** NOT RUN (no qualifying canonical run in the 2026-07-08..14 review window)
- **Commit:** `2fc3bb8f7dfd5d99ab4cc2b99aa95055465729e4` (`origin/main` documentation review baseline; not a tested commit)
- **Runtime:** N/A (no qualifying run imported)
- **Lane:** `W28R-3013`, `W28E-1882`, and seven-day candidate audit
- **Environment:** NOT IMPORTED - no candidate retains exact environment/configuration with a literal command and all other provenance
- **Command:** NOT IMPORTED - R2/R3 ledgers summarize commands or flows; R3 browser raw output records `args=<full>`; R4 documentation reconstructs command patterns
- **Evidence:** `docs/TEST-CANDIDATE-DISPOSITION.tsv`; immutable `W28R-3013-FINAL-PROOF-R2^{}` and `W28R-3013-FINAL-PROOF-R3^{}` at `09fd558f6c4d7be334a2c8e83efe85d1e4676e41`; remote evidence branch contains no cited R4 raw directory or R4 tag
- **Totals:** 0 tests | 0 passed | 0 failed | 0 errors | 0 skipped (canonical imported runs)

### Runtime truth

| Runtime | Canonical result | Disposition |
|---|---|---|
| CPython 3.12 | NOT RUN | The project rejects below-minimum runtimes; no full CPython 3.12 suite was run. |
| CPython 3.13.14, R4 claim | NOT IMPORTED | 493 total / 492 passed / 1 skipped was imported from a cited `r4-raw/junit` directory that is absent from the remote evidence branch; no R4 immutable tags exist, and the consolidated command is reconstructed. |
| CPython 3.13.14, R2/R3 | NOT IMPORTED | R2/R3 totals and fixes are retained, but original literal commands, exact timestamps, immutable tested commits, and environments are not present together. |
| N/A (Node/Playwright), R3 | NOT IMPORTED | Deployed 166/166 JUnit is immutable and timestamped, but the ledger command is summarized and the raw log omits the literal full arguments. |
| N/A (Node/Playwright), W28E-1882 | NOT IMPORTED | Final 165/165 JUnit lacks an exact command transcript and corrected immutable R2 anchor. |

## 2. Per-test status

No per-test rows are canonically imported for the review window.

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| _No canonical rows_ | - | - | - | - | R4-generated rows were removed because their cited remote evidence is absent. |

## 3. Noncanonical and adverse evidence

| Candidate | Runtime/scope | Preserved outcome | Disposition |
|---|---|---|---|
| W28R-3013 R2 | CPython 3.13 IT | 43 passed, 0 failed, 7 errors, 1 skipped | NOT IMPORTED |
| W28R-3013 R2 | CPython 3.13 AT | 25 passed, 4 failed, 0 errors, 1 skipped | NOT IMPORTED |
| W28R-3013 R2 | CPython 3.13 Docker IT rerun | 9 passed, 1 failed, 0 errors, 0 skipped | NOT IMPORTED |
| W28R-3013 R2 | Node/Playwright deployed | 97 passed, 8 failed, 10 skipped, 50 did not run | NOT IMPORTED |
| W28R-3013 R2 | CPython 3.13 UT/QT/ST | UT 326/326, QT 61/61, ST 30/30 | NOT IMPORTED |
| W28R-3013 R3 | CPython 3.13 | UT 336, QT 61, ST 30, AT 30 with 1 skip, IT 50 with 1 skip | NOT IMPORTED |
| W28R-3013 R3 | Node/Playwright deployed | 166 passed, 0 failed, 0 skipped | NOT IMPORTED |
| W28R-3013 R4 claim | CPython 3.13 | 492 passed, 1 skipped | NOT IMPORTED; cited remote artifacts absent |

The complete candidate review is [TEST-CANDIDATE-DISPOSITION.tsv](TEST-CANDIDATE-DISPOSITION.tsv).
