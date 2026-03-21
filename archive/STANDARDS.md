# file-mcp-server — Standards Alignment

## Adopted Platform Standards

| Standard | Scope | Current status |
|---|---|---|
| PS-00 Engineering principles | API-first, config delegation, UK English, no hardcoded values | Completed |
| PS-10 Architecture | Core/server separation (`file_tools/` library, `file_mcp_server/` transport) | Completed |
| PS-20 API contracts | Envelope responses, health endpoints, correlation IDs | Completed |
| PS-40 Logging/observability | Structured logs via `cloud_dog_logging`, audit JSONL | Completed |
| PS-70 IDAM | Auth/RBAC through `cloud_dog_idam` | Completed |
| PS-80 Config management | `cloud_dog_config` loader with typed model binding | Completed |
| PS-90 Security | Default-deny controls, secret redaction, path validation | Completed |
| PS-95 Testing | UT/ST/IT/AT/QT layout and `--env` enforcement | Completed |

## Implementation Notes

- Configuration loaded through `cloud_dog_config` in `src/file_tools/config/`.
- Logging and audit via `cloud_dog_logging` in `src/file_tools/audit/`.
- API application factory uses `cloud_dog_api_kit` in `src/file_mcp_server/server.py`.
- Authentication and RBAC via `cloud_dog_idam` in `src/file_mcp_server/idam_adapter.py` and `src/file_mcp_server/auth.py`.
- Storage backends: local filesystem, Google Drive (`src/file_tools/storage/`).
- Tests enforce `--env` selection in `tests/conftest.py`.
