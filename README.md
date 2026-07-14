---
template-id: T-RME
template-version: 1.0
applies-to: README.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 24cd1ac046fd3b0da63e4dcfc9cbdc0188ca6947
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T09:40:00Z
---

# File MCP Server

`file-mcp-server` exposes deterministic scoped file operations over HTTP, MCP, Web UI, and A2A-compatible metadata endpoints.

## Publication Quick Start

Prerequisites:

- Docker 24 or newer with BuildKit enabled
- Python 3.13 or newer if you run the package locally (NF-006 runtime contract)
- Public package source: `https://pypi.org/simple` (third-party deps). Cloud-Dog
  platform packages are published to the public index under the
  Cloud-Dog-External namespace, or installed from GitHub-mirrored source.

Build an isolated publication-test image:

```bash
PUBLICATION_TAG_SUFFIX=github-test ./docker-build.sh latest --variant public
```

Run the local smoke by executing the shell block in [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md) with `TAG=latest-gitea-test`.

The smoke run uses Docker defaults from [env-docker-defaults](env-docker-defaults) and probes the unified local surface on `8080`.

## Local Development

```bash
python3.13 -m venv .venv        # NF-006: Python 3.13 runtime contract
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://pypi.org/simple
```

See [EXTERNAL-BUILD.md](EXTERNAL-BUILD.md) for the full external/public build path.

Runtime configuration is loaded from the env file passed to `server_control.sh`, then from shell environment variables, then from `defaults.yaml`.

## Documentation

- [BUILD.md](BUILD.md)
- [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md)
- [env-docker-defaults](env-docker-defaults)

## Licence

Apache-2.0 - Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited

## Security & Publication Notes

Authentication and authorisation use the platform IDAM credential/cert model; do not commit secrets.
This public source mirror excludes internal operations material; build artefacts (e.g. the UI bundle) are regenerated at build time.

See the `examples/` directory and the sample configuration for usage examples.
