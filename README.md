# File MCP Server

Deterministic, scoped file tooling over MCP with FastMCP transports.

## Capabilities
- Filesystem: `read_file`, `write_file`, `copy_file`, `move_file`, `delete_file`, `list_dir`
- Search: `search_paths`, `search_content` (supports `max_depth`, `timeout_s`)
- Structured edits: JSON/YAML/XML/HTML/Markdown file tools
- Sed-like transactional edits: `sed_edit_file`
- Validation: `validate_text`, `validate_file`
- Diff/base64: `diff_text`, `diff_files`, `b64_*`
- Conversion: `convert_file`
- Auditing/snapshots integrated for mutating operations

## Setup
```bash
bash scripts/setup_venv.sh
source .venv/bin/activate
```

## Config Precedence
1. `os.environ`
2. `--env-path <file>`
3. `config.yaml`
4. `defaults.yaml`

## Run Server (Recommended)
Use the lifecycle wrapper script (requires explicit env file):

```bash
./server_control.sh --env private/env-test start
./server_control.sh --env private/env-test status
./server_control.sh --env private/env-test stop
```

Foreground mode:

```bash
./server_control.sh --env private/env-test serve
```

Equivalent direct CLI:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m file_mcp_server serve \
  --profile default \
  --env-path private/env-test \
  --config-path config.yaml \
  --defaults-path defaults.yaml \
  --pidfile .run/file-mcp-server.pid \
  --force-pidfile
```

## HTTP Interfaces
Transport is configured by `FILE_MCP_HTTP_TRANSPORT` (or config file `http.transport`):

- `streamable-http`: default MCP streamable HTTP interface on `http.mcp_path` (default `/mcp`)
- `http`: non-streaming HTTP style MCP transport on `http.mcp_path`
- `sse`: SSE transport on `http.events_path` (default `/events`)

Health endpoint:

```bash
curl -s http://127.0.0.1:8000/health
```

## Agent Usage Example (Python)
```python
import asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def main():
    async with Client(
        StreamableHttpTransport(
            "http://127.0.0.1:8000/mcp",
            headers={"Authorization": "Bearer secret"},
        )
    ) as client:
        result = await client.call_tool("read_file", {"path": "/tmp/example.txt"})
        print(result)

asyncio.run(main())
```

## Tool Examples
Search with controls:

```python
await client.call_tool(
    "search_content",
    {"query": "needle", "max_depth": 3, "timeout_s": 5, "max_results": 50},
)
```

Structured edit with dry-run:

```python
await client.call_tool(
    "json_set_file",
    {
        "path": "/tmp/data.json",
        "json_path": "/meta/version",
        "value": "1.2.3",
        "dry_run": True,
    },
)
```

Validate file:

```python
await client.call_tool("validate_file", {"path": "/tmp/data.yaml"})
```

## Testing
Full suite:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest
```

Current validated result:
- `132 passed`

Key integration flows:

```bash
PYTHONPATH=src pytest \
  tests/test_integration_config_matrix_harness_http.py \
  tests/test_integration_story_multitype_crud_http.py \
  tests/test_integration_iterative_cycle_guard_http.py
```

## Documentation Index
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TASKS.md`
- `docs/TESTS.md`
- `API_DOCUMENTATION.md`
- `openapi.json`
