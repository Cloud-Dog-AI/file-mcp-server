#!/usr/bin/env bash
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
