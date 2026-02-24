#!/usr/bin/env bash
# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${1:-private/env-google-drive}"

echo "============================================================"
echo "file-mcp-server Google Drive Setup"
echo "============================================================"
echo "Repository: ${ROOT_DIR}"
echo "Target env file: ${ENV_PATH}"
echo ""
echo "This setup will:"
echo "1) collect account + folder details"
echo "2) generate OAuth challenge URL"
echo "3) exchange auth code"
echo "4) validate folder access"
echo "5) save FILE_MCP_GDRIVE_* settings to env file"
echo ""
echo "Tip: if redirect URI is http://localhost, this script can auto-capture"
echo "the OAuth code from the callback in your browser."
echo "============================================================"
echo ""

cd "${ROOT_DIR}"

# Load Vault env automatically when available so setup can resolve
# FILE_MCP_GDRIVE_* defaults from platform config without manual export.
for VAULT_ENV in \
  "${ROOT_DIR}/private/env-vault" \
  "${ROOT_DIR}/../env-vault" \
  "${ROOT_DIR}/../env-vault-admin" \
  "${ROOT_DIR}/../cloud-dog-ai-private/private/vault_read.env"
do
  if [[ -f "${VAULT_ENV}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${VAULT_ENV}"
    set +a
    break
  fi
done

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "ERROR: python3 not found."
  exit 1
fi

if [[ "${PYTHON_BIN}" == ".venv/bin/python" ]]; then
  export PYTHONPATH="${ROOT_DIR}/src"
fi

exec "${PYTHON_BIN}" scripts/google_drive_setup.py --env-path "${ENV_PATH}"
