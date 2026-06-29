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
#
# file-mcp-server — PS-PREPROD-DEPLOY-SMOKE service-facing smoke entry point (W28E-1854).
#
# Runs the durable browser smoke (PDS-001..PDS-013) from the SSOT monorepo app
# (cloud-dog-ai-ui-monorepo/apps/file-mcp/tests/e2e/preprod-deploy-smoke.spec.ts)
# against the DEPLOYED preprod file-mcp service, AFTER the final deployed digest
# is live. Health-only / route-only / local-only proof is NOT acceptable
# (docs/standards/PS-PREPROD-DEPLOY-SMOKE.md §1, AGENT-LESSONS §6.157).
#
# Required config (no hardcoded secrets — RULES §2.3/§2.4/§5.3):
#   E2E_BASE_URL        default https://filemcpserver0.cloud-dog.net
#   E2E_WEB_USERNAME    default admin
#   E2E_WEB_PASSWORD    REQUIRED — approved preprod admin password. Source it from
#                       the approved preprod env / Vault, e.g. read
#                       dev.services.filemcpserver0.web_password from
#                       cloud_dog_ai/config, or export CLOUD_DOG_WEB_LOGIN_PASSWORD.
#   MONOREPO_ROOT       default /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
#
# Usage:
#   E2E_WEB_PASSWORD="<approved preprod admin password>" bash tests/smoke/run-preprod-deploy-smoke.sh
set -euo pipefail

E2E_BASE_URL="${E2E_BASE_URL:-https://filemcpserver0.cloud-dog.net}"
E2E_WEB_USERNAME="${E2E_WEB_USERNAME:-admin}"
E2E_WEB_PASSWORD="${E2E_WEB_PASSWORD:-${CLOUD_DOG_WEB_LOGIN_PASSWORD:-}}"
MONOREPO_ROOT="${MONOREPO_ROOT:-/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo}"
RESULTS_DIR="${RESULTS_DIR:-$(pwd)/working/preprod-deploy-smoke}"
APP_DIR="${MONOREPO_ROOT}/apps/file-mcp"

if [[ -z "${E2E_WEB_PASSWORD}" ]]; then
  echo "ERROR: E2E_WEB_PASSWORD (or CLOUD_DOG_WEB_LOGIN_PASSWORD) is required — source the approved preprod env/Vault." >&2
  exit 2
fi
if [[ ! -d "${APP_DIR}" ]]; then
  echo "ERROR: file-mcp app not found at ${APP_DIR}" >&2
  exit 2
fi

mkdir -p "${RESULTS_DIR}"
echo "PS-PREPROD-DEPLOY-SMOKE target: ${E2E_BASE_URL}"
echo "JUnit/HTML/trace results -> ${RESULTS_DIR}"

cd "${APP_DIR}"
E2E_BASE_URL="${E2E_BASE_URL}" \
E2E_WEB_USERNAME="${E2E_WEB_USERNAME}" \
E2E_WEB_PASSWORD="${E2E_WEB_PASSWORD}" \
PW_PREPROD_SMOKE_OUTPUT="${RESULTS_DIR}" \
  pnpm --filter @cloud-dog/app-file-mcp exec playwright test --config playwright.preprod-smoke.config.ts

echo "PS-PREPROD-DEPLOY-SMOKE complete. Evidence in ${RESULTS_DIR}"
