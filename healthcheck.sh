#!/usr/bin/env bash
# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

set -euo pipefail

HOST="${FILE_MCP_HEALTH_HOST:-127.0.0.1}"
PORT="${FILE_MCP_HEALTH_PORT:-8000}"
PATH_NAME="${FILE_MCP_HEALTH_PATH:-/health}"

curl -fsS "http://${HOST}:${PORT}${PATH_NAME}" >/dev/null
