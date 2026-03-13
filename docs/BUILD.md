# file-mcp-server Build Guide

## 1. Prerequisites

- Python 3.10+
- `pip` and virtualenv support
- Access to Cloud-Dog package index (`https://pypi.cloud-dog.net/simple/`)
- Docker 24+ (optional for container build/test)

## 2. Local venv setup

```bash
cd /opt/iac/Development/cloud-dog-ai/file-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

## 3. Source build

```bash
python -m build
```

## 4. Docker build

Use the project build wrapper (do not use ad-hoc `docker build`):

```bash
./docker-build.sh registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

## 5. Lint and type-check

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
```

## 6. Test execution by tier

All test runs must include `--env`.

```bash
# QT
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q

# UT
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q

# ST
.venv/bin/python -m pytest tests/system --env tests/env-ST -q

# IT
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q

# AT
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
.venv/bin/python -m pytest tests/application --env tests/env-AT -q
```

## 7. Local runtime start/stop

```bash
./server_control.sh --env tests/env-UT start
./server_control.sh --env tests/env-UT status
./server_control.sh --env tests/env-UT stop
```
