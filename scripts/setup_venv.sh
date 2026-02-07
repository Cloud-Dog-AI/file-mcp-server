#!/usr/bin/env bash
# File MCP Server - Venv Setup Script
#
# License: Apache 2.0
# Ownership: Cloud-Dog, Viewdeck Engineering Limited
# Description: Create/update the local Python virtual environment and install requirements.
# Requirements: BO1.5
# Tasks: T19, T20
# Architecture: 12. Testing Strategy
# Tests: N/A (script only)
# Recent Change History:
# - 2026-02-05: Initial venv setup script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${ROOT_DIR}/REQUIREMENTS.txt}"

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
  echo "REQUIREMENTS.txt not found at ${REQUIREMENTS_FILE}" >&2
  exit 1
fi

python3 -m venv "${VENV_DIR}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${REQUIREMENTS_FILE}"

echo "Venv ready at ${VENV_DIR}."
echo "Activate with: source ${VENV_DIR}/bin/activate"
