# file-mcp-server

Deterministic, scoped file operations exposed over MCP transports (`streamable-http`, `http`, `sse`).

License: Apache-2.0  
Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

## What this server provides

- Secure scoped file tools (`read_file`, `write_file`, `move_path`, `delete_file`, `list_dir`, etc.)
- Search and diff tools (`search_content`, `search_paths`, `diff_text`, `diff_files`)
- Structured document tooling (JSON, YAML, XML, HTML, Markdown)
- Validation, conversion, base64 utilities, and transactional sed-like edits
- Audit + snapshot support for mutating operations
- Configurable FastMCP HTTP runtime with API key auth

## Quick start (local Python)

```bash
bash scripts/setup_venv.sh
source .venv/bin/activate
mkdir -p private
cp docker-env.example private/env-test
PYTHONPATH=src ./server_control.sh --env private/env-test serve
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

## Docker quick start

Build:

```bash
./docker-build.sh cloud-dog/file-mcp-server:latest
```

Run on host network:

```bash
mkdir -p run/workspace run/logs
cp docker-env.example run/env.base
```

```bash
docker run --rm --name file-mcp-server \
  --network=host \
  -v "$(pwd)/run/workspace:/workspace" \
  -v "$(pwd)/run/logs:/workspace/logs" \
  -v "$(pwd)/run/env.base:/workspace/env.base:ro" \
  -e FILE_MCP_ENV_PATH=/workspace/env.base \
  cloud-dog/file-mcp-server:latest
```

Detailed Docker deployment, certs, multi-config, and remote host examples:
- `DOCKER-README.me`

## Configuration model

Precedence order (highest first):
1. Environment variables (`docker run -e ...`)
2. `--env-path` file(s) (comma-separated; left to right)
3. `config.yaml`
4. `defaults.yaml`

Primary Docker runtime variables:
- `FILE_MCP_ENV_PATH`
- `FILE_MCP_PROFILE`
- `FILE_MCP_CONFIG_PATH`
- `FILE_MCP_DEFAULTS_PATH`
- `FILE_MCP_TLS_CA_BUNDLE`

## CERTS support

Mount your certificate bundle into the container and point to it:

```bash
docker run --rm --network=host \
  -v "$(pwd)/certs:/app/certs:ro" \
  -e FILE_MCP_TLS_CA_BUNDLE=/app/certs/ca.crt \
  ...
```

Entry-point logic installs this CA into container trust and exports TLS env vars for Python/curl.

## Managing server lifecycle

### Native lifecycle helper

```bash
./server_control.sh --env private/env-test start
./server_control.sh --env private/env-test status
./server_control.sh --env private/env-test stop
```

### In container

```bash
docker exec -it file-mcp-server ./server_control.sh --env /workspace/env.base status
```

## MCP tools (summary)

- File tools: `read_file`, `write_file`, `copy_file`, `move_file`, `move_path`, `rename_path`, `delete_file`, `create_dir`, `chmod_path`, `list_dir`
- Search tools: `search_paths`, `search_content`
- Validation tools: `validate_text`, `validate_file`
- Diff and base64: `diff_text`, `diff_files`, `b64_encode`, `b64_decode`, `b64_encode_file`, `b64_decode_to_file`
- Structured tools: JSON/YAML/XML/HTML/Markdown get/set/merge/move/copy and `*_file` variants
- Advanced tools: `convert_file`, `sed_edit_file`, `meld_files` (optional)

## Testing

Full suite:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest
```

Docker-focused tests:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest tests/test_docker_container_runtime.py -k command -q
```

```bash
source .venv/bin/activate
FILE_MCP_RUN_DOCKER_TESTS=1 PYTHONPATH=src \
pytest tests/test_docker_container_runtime.py -q
```

Optional remote Docker host:

```bash
FILE_MCP_RUN_DOCKER_TESTS=1 FILE_MCP_DOCKER_HOST=tcp://remote-docker-host:2375 \
PYTHONPATH=src pytest tests/test_docker_container_runtime.py -q
```

## Additional docs

- `DOCKER-README.me`
- `API_DOCUMENTATION.md`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TASKS.md`
- `docs/TESTS.md`
