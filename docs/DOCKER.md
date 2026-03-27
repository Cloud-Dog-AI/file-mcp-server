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
