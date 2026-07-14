---
template-id: T-EXT
template-version: 1.0
applies-to: EXTERNAL-BUILD.md
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

# External Build Guide — file-mcp-server

This document lets an external builder build, run, and smoke-test
`file-mcp-server` from this published source tree alone, using only public
package sources. It assumes **no** access to any internal Cloud-Dog host,
registry, package index, or secret store.

## Package source strategy

- All third-party Python dependencies resolve from **public PyPI**
  (`https://pypi.org/simple`).
- Cloud-Dog platform packages (`cloud-dog-config`, `cloud-dog-logging`,
  `cloud-dog-api-kit`, `cloud-dog-idam`, `cloud-dog-db`, `cloud-dog-jobs`,
  `cloud-dog-storage`) must be available on the index you point the build at.
  On the public boundary they are published to public PyPI (Cloud-Dog-External
  namespace) or installed from the GitHub-mirrored source. If a platform
  package is not yet on your index, **stop and report the gap** — do not add a
  second index (`--extra-index-url`) as a workaround (PS-97 §3.3 / §4).
- A single index is used throughout. The default is `https://pypi.org/simple`.

## Prerequisites

| Component | Minimum | Notes |
|-----------|---------|-------|
| Docker    | 24+     | BuildKit enabled (default in 24+). Required for the container path. |
| Python    | 3.13    | Required only for the pure-source path and the lockfile check (NF-006 runtime contract). |
| Node.js   | 20+     | Only if you rebuild the UI bundle. The published tree ships a prebuilt `ui/`. |
| OS        | Linux, macOS, or Windows | Docker path is identical on all three. Shell snippets below are bash; on Windows use WSL2 or Git Bash. |

## Path A — Docker (recommended)

```bash
# 1. Build the public image. Override PYPI_INDEX_URL only if your boundary index
#    differs from public PyPI.
./docker-build.sh latest --variant public

# Or with an explicit index:
PYPI_URL=https://pypi.org/simple ./docker-build.sh latest --variant public
```

The build produces `cloud-dog/file-mcp-server:latest`. To build a throwaway,
registry-skipping publication-test image instead:

```bash
PUBLICATION_TAG_SUFFIX=github-test ./docker-build.sh latest --variant public
# image tag: cloud-dog/file-mcp-server:latest-github-test
```

### Smoke test

Run the shell block in [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md). It starts
the image with the checked-in [env-docker-defaults](env-docker-defaults) and
probes the unified HTTP surface on `127.0.0.1:8080`:

```bash
TAG=latest bash -c "$(sed -n '/^```bash$/,/^```$/p' PUBLICATION-SMOKE.md | sed '1d;$d')"
```

Expected: `RESULT: PASS`. Auth-gated `401/403` and redirect `3xx` responses
count as PASS because they prove the surface is up and routing.

## Path B — Pure source (no Docker)

```bash
# Linux / macOS
python3.13 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip

# Windows (PowerShell)
#   py -3.13 -m venv .venv
#   .venv\Scripts\Activate.ps1
#   python -m pip install --upgrade pip

# Single public index, no extra-index-url:
pip install --index-url https://pypi.org/simple -e .

# Provide a local env file (see docker-env.public.example for all keys):
cat > .env.local <<'ENV'
FILE_MCP_API_KEY_PRIMARY=change-me
FILE_MCP_HTTP_HOST=0.0.0.0
FILE_MCP_HTTP_PORT=8080
FILE_MCP_STORAGE_BACKEND=local
FILE_MCP_ROOT=./data/storage
ENV
mkdir -p ./data/storage

# Run the unified server:
python3 -m file_mcp_server serve --env-path ./.env.local

# Probe:
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/health
```

## Ports

| Port | Purpose | Source |
|------|---------|--------|
| 8080 | Unified HTTP surface (Web + API + MCP + A2A multiplexed) | `FILE_MCP_HTTP_PORT` / `CLOUD_DOG__WEB_SERVER__PORT` |
| 8081 | PS-92 MCP compatibility port (proxied → 8080) | `CLOUD_DOG__MCP_SERVER__PORT` |
| 8083 | PS-92 API compatibility port (proxied → 8080) | `CLOUD_DOG__API_SERVER__PORT` |

The entrypoint starts `scripts/port-proxy.py`, which forwards the PS-92
compatibility ports to the unified port. Only `8080` needs to be published.

## Environment

The service reads `FILE_MCP_*` keys and the PS-92 `CLOUD_DOG__*` port keys.
See [docker-env.public.example](docker-env.public.example) for the full set with
public placeholders. No internal host, registry, Vault path, or
`/opt/iac` path is required to build or run.

## Returning evidence

Place all build/smoke evidence under `evidence/external-build/` in your working
copy:

- `build.log` — full output of `docker-build.sh` (or the `pip install`).
- `image-digest.txt` — `docker inspect --format '{{.Id}}' cloud-dog/file-mcp-server:latest`.
- `smoke.log` — full output of the PUBLICATION-SMOKE run (must end `RESULT: PASS`).
- `pip-index-check.txt` — proof the build used a single index and no
  `--extra-index-url` (e.g. `grep -n 'index-url' build.log`).

Then produce a tarball and checksum and return both:

```bash
tar czf file-mcp-external-build-evidence.tgz evidence/external-build/
sha256sum file-mcp-external-build-evidence.tgz > file-mcp-external-build-evidence.tgz.sha256
```

Report any dependency-resolution gap (missing platform package on your index)
verbatim, with the failing `pip` line. Do not work around it with a second index.
