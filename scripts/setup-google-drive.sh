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
