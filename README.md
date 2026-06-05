# File MCP Server

`file-mcp-server` exposes deterministic scoped file operations over HTTP, MCP, Web UI, and A2A-compatible metadata endpoints.

## Publication Quick Start

Prerequisites:

- Docker 24 or newer with BuildKit enabled
- Python 3.10 or newer if you run the package locally
- Public package source: `https://gitea.cloud-dog.net/api/packages/Cloud-Dog-External/pypi/simple`

Build an isolated publication-test image:

```bash
PUBLICATION_TAG_SUFFIX=gitea-test ./docker-build.sh latest
```

Run the local smoke by executing the shell block in [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md) with `TAG=latest-gitea-test`.

The smoke run uses Docker defaults from [env-docker-defaults](env-docker-defaults) and probes the unified local surface on `8080`.

## Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --extra-index-url https://gitea.cloud-dog.net/api/packages/Cloud-Dog-External/pypi/simple
```

Runtime configuration is loaded from the env file passed to `server_control.sh`, then from shell environment variables, then from `defaults.yaml`.

## Documentation

- [BUILD.md](BUILD.md)
- [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md)
- [env-docker-defaults](env-docker-defaults)

## Licence

Apache-2.0 - Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited
