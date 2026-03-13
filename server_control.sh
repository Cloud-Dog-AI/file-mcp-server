#!/usr/bin/env bash
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

# file-mcp-server lifecycle helper
# Requires an explicit env file to match project rules.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<USAGE
Usage:
  ./server_control.sh --env <env-file> [--config <config.yaml>] [--defaults <defaults.yaml>] [--profile <name>] [--pidfile <pidfile>] <start|stop|status|restart|serve>

Examples:
  ./server_control.sh --env private/env-test start
  ./server_control.sh --env private/env-test status
  ./server_control.sh --env private/env-test stop
  ./server_control.sh --env private/env-test restart
  ./server_control.sh --env private/env-test serve
USAGE
}

ENV_PATH=""
CONFIG_PATH="config.yaml"
DEFAULTS_PATH="defaults.yaml"
PROFILE="default"
PIDFILE=".run/file-mcp-server.pid"
ACTION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_PATH="${2:-}"
      shift 2
      ;;
    --config)
      CONFIG_PATH="${2:-}"
      shift 2
      ;;
    --defaults)
      DEFAULTS_PATH="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --pidfile)
      PIDFILE="${2:-}"
      shift 2
      ;;
    start|stop|status|restart|serve)
      ACTION="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$ENV_PATH" ]]; then
  echo "ERROR: --env <env-file> is required." >&2
  usage
  exit 2
fi

if [[ ! -f "$ENV_PATH" ]]; then
  echo "ERROR: env file not found: $ENV_PATH" >&2
  exit 2
fi

if [[ -z "$ACTION" ]]; then
  echo "ERROR: action is required (start|stop|status|restart|serve)." >&2
  usage
  exit 2
fi

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

COMMON_ARGS=(
  --profile "$PROFILE"
  --env-path "$ENV_PATH"
  --config-path "$CONFIG_PATH"
  --defaults-path "$DEFAULTS_PATH"
  --pidfile "$PIDFILE"
)

export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

run_cmd() {
  local clear_vault=1
  if grep -Eq '^[[:space:]]*VAULT_[A-Z0-9_]*=' "$ENV_PATH"; then
    clear_vault=0
  fi

  if [[ "$clear_vault" -eq 1 ]]; then
    env \
      VAULT_ADDR= \
      VAULT_TOKEN= \
      VAULT_NAMESPACE= \
      VAULT_MOUNT_POINT= \
      VAULT_CONFIG_PATH= \
      "$PYTHON_BIN" -m file_mcp_server "$@"
    return
  fi

  "$PYTHON_BIN" -m file_mcp_server "$@"
}

case "$ACTION" in
  start)
    run_cmd start "${COMMON_ARGS[@]}"
    ;;
  stop)
    run_cmd stop --pidfile "$PIDFILE"
    ;;
  status)
    run_cmd status --pidfile "$PIDFILE"
    ;;
  restart)
    run_cmd stop --pidfile "$PIDFILE" || true
    run_cmd start "${COMMON_ARGS[@]}" --force
    ;;
  serve)
    run_cmd serve "${COMMON_ARGS[@]}" --force-pidfile
    ;;
  *)
    echo "Unsupported action: $ACTION" >&2
    exit 2
    ;;
esac
