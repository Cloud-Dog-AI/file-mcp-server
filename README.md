# file-mcp-server

`file-mcp-server` is the Cloud-Dog AI platform file tooling service, exposing deterministic scoped file operations over MCP and HTTP for automation clients, integration harnesses, and UI consumers.

## Quick Start

Prerequisites:
- Python 3.10+
- `pip` and virtualenv support
- Docker (optional, for container workflows)

Install:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://<internal-pypi>/simple/
```

Run:
```bash
./server_control.sh --env tests/env-ST start all
```

Test:
```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
```

Verified local default ports from [defaults.yaml](defaults.yaml):
- API `8060`
- Web `8061`
- MCP `8062`
- A2A `8063`

## Architecture Overview

The project is split into a transport layer (`src/file_mcp_server/`) and reusable tooling layer (`src/file_tools/`) with strict config/auth/audit controls.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## API Interfaces

| Interface | Surface | Reference |
|---|---|---|
| REST | Health/admin/runtime endpoints | [docs/API-REFERENCE.md](docs/API-REFERENCE.md) |
| MCP | Tool discovery and tool execution (`/mcp`) | [docs/API-REFERENCE.md](docs/API-REFERENCE.md) |
| A2A | `/a2a/health` auth contract in local runtime flows | [docs/API-REFERENCE.md](docs/API-REFERENCE.md) |
| Web UI | SPA shell at `/` (routes include `/login`, `/search`, `/storage-profiles`) plus dynamic `/runtime-config.js` | [docs/BUILD.md](docs/BUILD.md) |

## Configuration

Environment/configuration reference: [docs/ENV-REFERENCE.md](docs/ENV-REFERENCE.md)

Build/deploy guidance: [docs/BUILD.md](docs/BUILD.md), [docs/DEPLOY.md](docs/DEPLOY.md)

## Validation Snapshot

Verified on `2026-04-16` during W28A-961:
- Unit: `177 passed`
- Integration: `37 passed, 10 skipped`
- Application: `25 passed, 1 skipped`
- Monorepo Playwright app suite: `47 passed (2.1m)`
- Local container build: `./docker-build.sh test` → `Build OK: cloud-dog/file-mcp-server:test`
- Registry push: `<internal-registry>:443/cloud-dog/file-mcp-server:latest@sha256:27c97601f7b2ee602e59f2a6b203478b2aa556444b6333d16ef188ba6b4ca6f5`

## Platform Packages

| Package | Usage | Version constraint |
|---|---|---|
| `cloud_dog_config` | Config loading and Vault interpolation | `>=0.2.0` |
| `cloud_dog_logging` | Structured operational/audit logging | `>=0.2.0` |
| `cloud_dog_api_kit` | API app and health contracts | `>=0.2.0` |
| `cloud_dog_idam` | Auth/RBAC integration | `>=0.2.0` |
| `cloud_dog_db` | DB settings/engine/migration/probe | `>=0.1.0` |

## Standards Alignment

| Standard | Status |
|---|---|
| PS-00 | ✅ |
| PS-10 | ✅ |
| PS-20 | ✅ |
| PS-40 | ✅ |
| PS-70 | ✅ |
| PS-80 | ✅ |
| PS-90 | ✅ |
| PS-95 | ✅ |

## Documentation Links

| File | Purpose |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Functional/non-functional requirements |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Runtime and module architecture |
| [docs/TESTS.md](docs/TESTS.md) | Test catalogue and execution history |
| [docs/TASKS.md](docs/TASKS.md) | Requirement-task mapping |
| [docs/BUILD.md](docs/BUILD.md) | Local build/test procedures |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Deployment options and operational guidance |
| [docs/API-REFERENCE.md](docs/API-REFERENCE.md) | REST/MCP/A2A API contracts |
| [docs/ENV-REFERENCE.md](docs/ENV-REFERENCE.md) | Environment variable reference |
| [openapi.json](openapi.json) | OpenAPI document |
| [RULES.md](RULES.md) | Project rules extending platform rules |
| [CONTEXT-SUMMARY.md](CONTEXT-SUMMARY.md) | Current project context and handoff notes |

---

## Licence

Apache-2.0 — Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited
