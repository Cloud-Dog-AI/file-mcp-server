# file-mcp-server Architecture

**Version:** 1.0
**Date:** 2026-03-08
**Standards:** PS-00, PS-10, PS-20, PS-40, PS-70, PS-80, PS-90, PS-95
**Platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`

---

## 1. Overview

`file-mcp-server` provides **file management tooling** through:
- MCP-compatible A2A tools (language-neutral JSON IO)
- HTTP API (FastAPI) used by WebUI and automation clients

It supports:
- Local filesystem operations (read, write, edit, search, diff)
- Google Drive integration (admin, upload, download)
- Multiple storage backends with backend-specific configuration
- File conversion and validation pipelines
- RBAC with pluggable enterprise auth
- Endpoint health monitoring

**Design principles**
- No hard-coded values (env → .env → config.yaml → defaults.yaml)
- Tools separated from server transport (`file_tools/` vs `file_mcp_server/`)
- Deterministic, auditable operations
- POSIX-friendly behaviours (atomic writes, scope isolation)

---

## 2. Repository Layout

```
repo/
  defaults.yaml
  pyproject.toml
  server_control.sh
  docker-build.sh
  Dockerfile
  RULES.md
  STANDARDS.md
  ARCHITECTURE.md
  src/
    file_tools/          # Core library (transport-independent)
      audit/             # Audit trail and event logging
      config/            # Configuration loading and typed models
      convert/           # File format conversion
      diff/              # Diff and patch operations
      edit/              # File editing primitives
      io/                # Low-level IO operations
      scope/             # Workspace scope isolation
      search/            # File search and grep
      storage/           # Storage backends (local, Google Drive)
      tools/             # MCP tool definitions
      validate/          # Input validation
    file_mcp_server/     # Server transport layer
      auth.py            # Authentication middleware
      db/                # Database layer
      endpoint_health.py # Health monitoring
      google_drive_admin.py # Google Drive admin interface
      idam_adapter.py    # IDAM integration adapter
      lifecycle.py       # Server lifecycle management
      main.py            # Entry point
      server.py          # FastAPI application factory
      server_runtime.py  # Runtime configuration and startup
  tests/
    unit/                # UT tier
    system/              # ST tier
    integration/         # IT tier
    application/         # AT tier
    env-*                # Environment files per tier
```

---

## 3. Core Components

### 3.1 file_tools (library)
- **config/**: `cloud_dog_config` loader with typed model binding
- **storage/**: Pluggable storage backends — local filesystem and Google Drive
- **audit/**: `cloud_dog_logging` structured audit events
- **tools/**: MCP tool definitions (read, write, edit, search, diff, convert, validate)
- **scope/**: Workspace isolation per session
- **convert/**: File format conversion pipeline
- **search/**: Content search with regex and glob support

### 3.2 file_mcp_server (transport)
- **server.py**: FastAPI application factory via `cloud_dog_api_kit`
- **idam_adapter.py**: Authentication and RBAC via `cloud_dog_idam`
- **endpoint_health.py**: Health check endpoints for all backends
- **google_drive_admin.py**: Google Drive admin operations
- **lifecycle.py**: Server start/stop lifecycle
- **server_runtime.py**: Runtime configuration, startup sequencing, tool registration

---

## 4. Configuration

Configuration hierarchy (highest priority first):
1. Environment variables
2. `.env` file
3. `config.yaml`
4. `defaults.yaml`

All configuration loaded through `cloud_dog_config`. No direct `os.environ` access in business logic.

---

## 5. Testing Strategy

| Tier | Scope | Env file |
|------|-------|----------|
| UT | Unit tests, no external deps | `tests/env-UT-local-docker` |
| ST | System tests, mocked externals | `tests/env-ST-local-docker` |
| IT | Integration tests, real Docker deps | `tests/env-IT-local-docker` |
| AT | Application tests, full stack | `tests/env-AT-local-docker` |

All pytest invocations require `--env <env-file>` per `tests/conftest.py`.
