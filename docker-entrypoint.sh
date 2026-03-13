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

echo "============================================================"
echo "file-mcp-server container"
echo "============================================================"
echo "Mode: ${1:-serve}"
echo "Python: $(python3 --version)"
echo "Working dir: $(pwd)"
echo "============================================================"

mkdir -p /app/.run /app/logs /app/certs

install_ca_bundle() {
  # Support both the generic container trust bundle and the remote-storage TLS
  # bundle path. For remote backends, `FILE_MCP_STORAGE_TLS_CA_BUNDLE` is the
  # canonical config value used by backend clients (requests/ftplib TLS).
  local ca_path="${FILE_MCP_TLS_CA_BUNDLE:-${FILE_MCP_STORAGE_TLS_CA_BUNDLE:-${REQUESTS_CA_BUNDLE:-}}}"
  if [[ -z "${ca_path}" ]]; then
    return 0
  fi

  if [[ -f "${ca_path}" ]]; then
    echo "Installing CA bundle: ${ca_path}"
    cp "${ca_path}" /usr/local/share/ca-certificates/file-mcp-custom-ca.crt
    # Don't hard-fail container startup if the bundle can't be installed into
    # the system trust store; the server can still use the bundle directly via
    # `FILE_MCP_STORAGE_TLS_CA_BUNDLE` and standard TLS env vars.
    update-ca-certificates || echo "WARNING: update-ca-certificates failed; continuing"
  else
    echo "WARNING: CA bundle file not found: ${ca_path}"
  fi
}

install_ca_bundle

export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"

PROFILE="${FILE_MCP_PROFILE:-default}"
ENV_PATH="${FILE_MCP_ENV_PATH:-}"
CONFIG_PATH="${FILE_MCP_CONFIG_PATH:-/app/config.yaml}"
DEFAULTS_PATH="${FILE_MCP_DEFAULTS_PATH:-/app/defaults.yaml}"
PIDFILE="${FILE_MCP_PIDFILE:-/app/.run/file-mcp-server.pid}"

build_effective_env_file() {
  local source_paths="$1"
  local output_path="/tmp/file-mcp-container.env"
  local path=""
  local line=""
  local key=""
  local value=""
  local -a ordered_keys=()
  local -a paths=()
  declare -A values=()
  declare -A seen=()

  add_pair() {
    local in_key="$1"
    local in_value="$2"
    if [[ -z "${in_key}" ]]; then
      return
    fi
    if [[ -z "${seen["${in_key}"]+x}" ]]; then
      ordered_keys+=("${in_key}")
      seen["${in_key}"]=1
    fi
    values["${in_key}"]="${in_value}"
  }

  parse_env_file() {
    local env_file="$1"
    if [[ ! -f "${env_file}" ]]; then
      echo "WARNING: env file not found at ${env_file}. Continuing."
      return
    fi
    while IFS= read -r line || [[ -n "${line}" ]]; do
      line="${line%$'\r'}"
      [[ -z "${line}" ]] && continue
      [[ "${line}" == \#* ]] && continue
      if [[ "${line}" == export\ * ]]; then
        line="${line#export }"
      fi
      if [[ ! "${line}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
        continue
      fi
      key="${line%%=*}"
      value="${line#*=}"
      add_pair "${key}" "${value}"
    done < "${env_file}"
  }

  if [[ -n "${source_paths}" ]]; then
    IFS=',' read -r -a paths <<< "${source_paths}"
    for path in "${paths[@]}"; do
      parse_env_file "${path}"
    done
  fi

  while IFS='=' read -r key value; do
    if [[ "${key}" == FILE_MCP_* ]]; then
      add_pair "${key}" "${value}"
    fi
  done < <(env)

  : > "${output_path}"
  for key in "${ordered_keys[@]}"; do
    printf "%s=%s\n" "${key}" "${values["${key}"]}" >> "${output_path}"
  done

  printf "%s\n" "${output_path}"
}

# Build a single effective env file where FILE_MCP_* process env values override
# loaded env-file values, matching required precedence.
ENV_PATH="$(build_effective_env_file "${ENV_PATH}")"
export FILE_MCP_ACTIVE_ENV_PATH="${ENV_PATH}"

case "${1:-serve}" in
  serve)
    ARGS=(
      --profile "${PROFILE}"
      --config-path "${CONFIG_PATH}"
      --defaults-path "${DEFAULTS_PATH}"
      --pidfile "${PIDFILE}"
      --force-pidfile
    )
    if [[ -n "${ENV_PATH}" ]]; then
      ARGS+=(--env-path "${ENV_PATH}")
    fi
    exec python3 -m file_mcp_server serve "${ARGS[@]}"
    ;;
  start|stop|status|restart)
    CONTROL_ARGS=(
      --config "${CONFIG_PATH}"
      --defaults "${DEFAULTS_PATH}"
      --profile "${PROFILE}"
      --pidfile "${PIDFILE}"
      "$1"
    )
    if [[ -n "${ENV_PATH}" ]]; then
      CONTROL_ARGS=(--env "${ENV_PATH}" "${CONTROL_ARGS[@]}")
    fi
    exec ./server_control.sh "${CONTROL_ARGS[@]}"
    ;;
  shell)
    exec /bin/bash
    ;;
  *)
    exec "$@"
    ;;
esac
