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
  ./server_control.sh --env <env-file> [--config <config.yaml>] [--defaults <defaults.yaml>] [--profile <name>] [--pidfile <pidfile>] <start|stop|status|restart|serve> [all|api|web|mcp|a2a]

Examples:
  ./server_control.sh --env tests/env-IT start all
  ./server_control.sh --env tests/env-IT status api
  ./server_control.sh --env tests/env-IT stop all
  ./server_control.sh --env tests/env-IT restart mcp
  ./server_control.sh --env tests/env-IT serve api
USAGE
}

ENV_PATH=""
CONFIG_PATH="config.yaml"
DEFAULTS_PATH="defaults.yaml"
PROFILE="default"
PIDFILE=".run/file-mcp-server.pid"
PIDFILE_CUSTOM=0
ACTION=""
COMPONENT=""
COMPONENT_ORDER=(api web mcp a2a)

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
      PIDFILE_CUSTOM=1
      shift 2
      ;;
    start|stop|status|restart|serve)
      if [[ -n "$ACTION" ]]; then
        echo "ERROR: multiple actions provided ($ACTION, $1)." >&2
        exit 2
      fi
      ACTION="$1"
      shift
      ;;
    all|api|web|mcp|a2a)
      if [[ -n "$COMPONENT" ]]; then
        echo "ERROR: multiple components provided ($COMPONENT, $1)." >&2
        exit 2
      fi
      COMPONENT="$1"
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

if [[ -z "$COMPONENT" ]]; then
  COMPONENT="api"
fi

if [[ "$ACTION" == "serve" && "$COMPONENT" == "all" ]]; then
  echo "ERROR: serve only supports one component (api|web|mcp|a2a)." >&2
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
)

export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

run_cmd() {
  local keep_vault=0
  if grep -Eq '^[[:space:]]*VAULT_[A-Z0-9_]*=' "$ENV_PATH"; then
    keep_vault=1
  fi
  if grep -Eq '\$\{[[:space:]]*vault\.' "$ENV_PATH"; then
    keep_vault=1
  fi

  if [[ "$keep_vault" -eq 0 ]]; then
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

component_pidfile() {
  local component="$1"
  if [[ "$PIDFILE_CUSTOM" -eq 1 ]]; then
    echo "$PIDFILE"
    return
  fi
  case "$component" in
    api) echo ".run/file-mcp-server.pid" ;;
    web) echo ".run/file-mcp-server-web.pid" ;;
    mcp) echo ".run/file-mcp-server-mcp.pid" ;;
    a2a) echo ".run/file-mcp-server-a2a.pid" ;;
    *)
      echo "ERROR: unsupported component '$component'" >&2
      exit 2
      ;;
  esac
}

start_component() {
  local component="$1"
  local force_flag="${2:-0}"
  local pidfile
  pidfile="$(component_pidfile "$component")"
  local args=(
    start
    "${COMMON_ARGS[@]}"
    --server-role "$component"
    --pidfile "$pidfile"
  )
  if [[ "$force_flag" -eq 1 ]]; then
    args+=(--force)
  fi
  run_cmd "${args[@]}"
}

stop_component() {
  local component="$1"
  local pidfile
  pidfile="$(component_pidfile "$component")"
  run_cmd stop --pidfile "$pidfile"
}

status_component() {
  local component="$1"
  local pidfile
  pidfile="$(component_pidfile "$component")"
  run_cmd status --pidfile "$pidfile"
}

restart_component() {
  local component="$1"
  stop_component "$component" || true
  start_component "$component" 1
}

case "$ACTION" in
  start)
    if [[ "$COMPONENT" == "all" ]]; then
      started=()
      for item in "${COMPONENT_ORDER[@]}"; do
        if start_component "$item"; then
          started+=("$item")
        else
          for undo in "${started[@]}"; do
            stop_component "$undo" || true
          done
          exit 1
        fi
      done
    else
      start_component "$COMPONENT"
    fi
    ;;
  stop)
    if [[ "$COMPONENT" == "all" ]]; then
      for item in "${COMPONENT_ORDER[@]}"; do
        stop_component "$item" || true
      done
    else
      stop_component "$COMPONENT"
    fi
    ;;
  status)
    if [[ "$COMPONENT" == "all" ]]; then
      for item in "${COMPONENT_ORDER[@]}"; do
        status_component "$item"
      done
    else
      status_component "$COMPONENT"
    fi
    ;;
  restart)
    if [[ "$COMPONENT" == "all" ]]; then
      for item in "${COMPONENT_ORDER[@]}"; do
        stop_component "$item" || true
      done
      for item in "${COMPONENT_ORDER[@]}"; do
        start_component "$item" 1
      done
    else
      restart_component "$COMPONENT"
    fi
    ;;
  serve)
    pidfile="$(component_pidfile "$COMPONENT")"
    run_cmd serve "${COMMON_ARGS[@]}" --server-role "$COMPONENT" --pidfile "$pidfile" --force-pidfile
    ;;
  *)
    echo "Unsupported action: $ACTION" >&2
    exit 2
    ;;
esac
