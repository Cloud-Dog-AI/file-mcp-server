---
template-id: T-DOK
template-version: 1.0
applies-to: docs/DOCKER.md
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

# Docker Guide

## Build
```bash
docker build -t file-mcp:latest .
```

## Run
```bash
docker run --rm -it --env-file .env -p 8080:8080 -p 8081:8081 -p 8082:8082 -p 8083:8083 file-mcp:latest
```

## Push
```bash
docker tag file-mcp:latest registry.example.com/your-team/file-mcp:latest
docker push registry.example.com/your-team/file-mcp:latest
```

## Compose Files
- `docker-compose.local.yml`

## Notes
- Keep secrets out of committed compose files and environment examples.
- Use `docs/DEPLOY.md` for Vault-backed runs and custom CA certificate instructions.
