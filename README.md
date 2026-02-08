# File MCP Server

Deterministic, scoped file tooling over MCP/JSON-RPC with FastMCP HTTP transport.

## What It Provides
- Scoped file operations: `read_file`, `write_file`, `copy_file`, `move_file`, `delete_file`, `list_dir`
- Search: `search_paths`, `search_content` (with optional `max_depth` and `timeout_s`)
- Structured edits: JSON/YAML/XML/HTML/Markdown file mutation tools
- Sed-like transactional text editing: `sed_edit_file`
- Validation: `validate_text`, `validate_file`
- Audit and snapshots for mutation attempts
- Conversion pipeline with optional external backends

## Repo Layout
- `src/`: production code
- `tests/`: unit/system/integration/application tests
- `docs/`: requirements/tasks/tests/architecture docs
- `private/`: env files (gitignored)
- `working/`, `archive/`, `storage/`, `tmp/`: runtime and workflow directories

## Local Setup
1. Create venv and install dependencies:
```bash
bash scripts/setup_venv.sh
```
2. Activate venv:
```bash
source .venv/bin/activate
```

## Configuration
Configuration precedence is:
1. `os.environ`
2. env file (`--env-path <path>`)
3. `config.yaml`
4. `defaults.yaml`

For local testing, create an env file under `private/` (for example `private/env-test`) and provide API key and scoped root values.

## Run Server
Serve profile `default` with explicit config/env paths:
```bash
source .venv/bin/activate
PYTHONPATH=src python -m file_mcp_server serve \
  --profile default \
  --env-path private/env-test \
  --config-path config.yaml \
  --defaults-path defaults.yaml \
  --pidfile tmp/file-mcp.pid \
  --force-pidfile
```

Health endpoint (default):
- `GET /health`

MCP endpoint (default streamable HTTP):
- `POST /mcp`

## Run Tests
Run the full suite:
```bash
source .venv/bin/activate
PYTHONPATH=src pytest
```

Run a single test file:
```bash
source .venv/bin/activate
PYTHONPATH=src pytest tests/test_system_validate_file_tool.py
```

Run the end-to-end integration harness stories:
```bash
source .venv/bin/activate
PYTHONPATH=src pytest tests/test_integration_config_matrix_harness_http.py tests/test_integration_story_multitype_crud_http.py tests/test_integration_iterative_cycle_guard_http.py
```

Latest validated run in this workspace:
- `131 passed, 2 skipped` (`PYTHONPATH=src pytest`)

## API Docs
- Human-readable API docs: `API_DOCUMENTATION.md`
- OpenAPI document: `openapi.json`

## Notes
- No LLM integration.
- All file operations are scope-constrained.
- Mutation paths are audited; snapshots are controlled by profile configuration.
- Real backend conversion tests for `pandoc`/`soffice` run when available; otherwise they are explicitly skipped.
