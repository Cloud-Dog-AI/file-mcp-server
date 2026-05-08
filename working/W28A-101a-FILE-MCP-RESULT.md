# W28A-101a File MCP Python 3.12 Rerun Result

Date: 2026-05-08
Repo: `file-mcp-server`
Instruction: `cloud-dog-ai-platform-standards/working/instructions/W28A-101a-file-mcp-PYTHON-312-RERUN-2026-05-08.md`

## Contract Readback

- Goal: validate `file-mcp-server` on Python 3.12.13 after the PS-100 migration, rerun all applicable UT/ST/IT/AT/QT layers, build/package evidence, Docker build evidence, `server_control.sh` smoke evidence, stale Python reference scan, and `git diff --check`.
- Runtime fallback posture: no Python 3.10/3.11 build, Docker, package, or test-runner references are active.
- No local DB/container fallback was introduced. Existing explicit IT/AT skips remain fail-visible with reasons.
- Working-tree exception before this task: `.venv.ps100-backup-20260508T114656Z/` was already untracked and remains outside the submitted code/evidence set.

## Changes Made

- Added missing dev/test dependency `fastmcp>=3.2,<4.0` so ST/IT/AT test clients collect under the Python 3.12 venv.
- Replaced direct MCP transport `FastAPI(...)` construction with `cloud_dog_api_kit.factory.create_app(...)`.
- Fixed WebUI file editor bundle handling so MCP string payloads unwrap `structuredContent.value` and save the latest editor value reliably.
- Updated QT compliance metadata and traceability:
  - documented bootstrap env and local loopback carve-outs in compliance allowlists;
  - kept explicit IT/AT skip sites allowlisted and auditable;
  - added FR1.47 traceability mappings and corrected stale `idam_adapter.py` mappings;
  - corrected UK spelling in public docs/OpenAPI descriptions;
  - made the TESTS duplicate-ID parser ignore IDs embedded in path names.

## Evidence

| Gate | Command | Result | Log |
|---|---|---|---|
| Runtime guard | `.venv/bin/python cloud-dog-ai-platform-standards/working/templates/python-runtime-guard.py` | PASS, Python 3.12.13, `runtime_guard=pass` | `working/w28a-101-ps100-python-runtime-guard.log` |
| Diff check | `git diff --check` | PASS | `working/w28a-101-diff-check.log` |
| UT | `.venv/bin/python -m pytest tests/unit --env tests/env-UT --basetemp working/pytest-tmp-ut -q` | PASS: `182 passed, 1 warning` | `working/w28a-101-ut.log` |
| ST | `.venv/bin/python -m pytest tests/system --env tests/env-ST --basetemp working/pytest-tmp-st -q` | PASS: `30 passed` | `working/w28a-101-st.log` |
| IT | `.venv/bin/python -m pytest tests/integration --env tests/env-IT --basetemp working/pytest-tmp-it -q -rs` | PASS: `38 passed, 10 skipped` | `working/w28a-101-it.log` |
| AT | `server_control.sh --env tests/env-AT start all` then `.venv/bin/python -m pytest tests/application --env tests/env-AT --basetemp working/pytest-tmp-at -q -rs` | PASS: `25 passed, 1 skipped` | `working/w28a-101-at.log` |
| QT | `.venv/bin/python -m pytest tests/quality --env tests/env-QT --basetemp working/pytest-tmp-qt -q -rs` | PASS: `60 passed` | `working/w28a-101-qt.log` |
| Package build | `.venv/bin/python -m build --sdist --wheel` | PASS: sdist and wheel built | `working/w28a-101-build.log` |
| Docker build | `./docker-build.sh w28a-101a-python312` | PASS: `Build OK: cloud-dog/file-mcp-server:w28a-101a-python312` | `working/w28a-101-docker-build.log` |
| Server smoke | `server_control.sh --env tests/env-ST start/status/stop all` plus API/Web/MCP/A2A HTTP probes | PASS: all endpoints returned 200 | `working/w28a-101-server-smoke.log` |
| Python reference scan | grep active build/docker/package/test-runner/runtime paths for Python 3.10/3.11 refs | PASS: no hits | `working/w28a-101-python-reference-scan.log` |

## Skips And Warnings

- UT warning: existing `PytestUnknownMarkWarning` for `pytest.mark.unit` in `tests/unit/UT_CFG06_A2AEvents/test_config_change_events.py`.
- IT skips: remote WebDAV/FTP/S3 live backend credentials/contracts are not configured in `tests/env-IT`; GDrive live test remains deferred pending web OAuth interface W28A-121.
- AT skip: GDrive OAuth live application test remains deferred pending web OAuth interface W28A-121.
- No xfails were used.

## Final State

- Runtime: Python 3.12.13 venv confirmed.
- All required executable gates are green.
- Generated pytest temp directories, screenshots, package build outputs, and transient build metadata were removed after evidence capture.
- Remaining untracked item: `.venv.ps100-backup-20260508T114656Z/`, pre-existing venv backup outside submitted changes.
