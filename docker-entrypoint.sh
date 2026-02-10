#!/usr/bin/env bash
# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

set -euo pipefail

echo "============================================================"
echo "file-mcp-server container"
echo "============================================================"
echo "Mode: ${1:-serve}"
echo "Python: $(python3 --version)"
echo "Working dir: $(pwd)"
echo "============================================================"

mkdir -p /app/.run /app/logs /app/certs

install_ca_bundle() {
  local ca_path="${FILE_MCP_TLS_CA_BUNDLE:-${REQUESTS_CA_BUNDLE:-}}"
  if [[ -z "${ca_path}" ]]; then
    return 0
  fi

  if [[ -f "${ca_path}" ]]; then
    echo "Installing CA bundle: ${ca_path}"
    cp "${ca_path}" /usr/local/share/ca-certificates/file-mcp-custom-ca.crt
    update-ca-certificates
  else
    echo "WARNING: FILE_MCP_TLS_CA_BUNDLE file not found: ${ca_path}"
  fi
}

install_ca_bundle

export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"

PROFILE="${FILE_MCP_PROFILE:-default}"
ENV_PATH="${FILE_MCP_ENV_PATH:-/app/env-docker-defaults}"
CONFIG_PATH="${FILE_MCP_CONFIG_PATH:-/app/config.yaml}"
DEFAULTS_PATH="${FILE_MCP_DEFAULTS_PATH:-/app/defaults.yaml}"
PIDFILE="${FILE_MCP_PIDFILE:-/app/.run/file-mcp-server.pid}"

if [[ ! -f "${ENV_PATH%%,*}" ]]; then
  echo "WARNING: env file not found at ${ENV_PATH}. Continuing with OS environment only."
fi

case "${1:-serve}" in
  serve)
    exec python3 -m file_mcp_server serve \
      --profile "${PROFILE}" \
      --env-path "${ENV_PATH}" \
      --config-path "${CONFIG_PATH}" \
      --defaults-path "${DEFAULTS_PATH}" \
      --pidfile "${PIDFILE}" \
      --force-pidfile
    ;;
  start|stop|status|restart)
    exec ./server_control.sh \
      --env "${ENV_PATH}" \
      --config "${CONFIG_PATH}" \
      --defaults "${DEFAULTS_PATH}" \
      --profile "${PROFILE}" \
      --pidfile "${PIDFILE}" \
      "$1"
    ;;
  shell)
    exec /bin/bash
    ;;
  *)
    exec "$@"
    ;;
esac
