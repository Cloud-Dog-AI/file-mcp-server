#!/usr/bin/env bash
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

# file-mcp-server — Docker Build Script (PS-91)
# Uses BuildKit secret mount for private PyPI auth — credentials never enter image layers.
# Pattern: identical to git-mcp-server (the reference).
set -euo pipefail

VERSION="${1:-latest}"
CONTAINER="file-mcp-server"
FOLDER="cloud-dog"
REGISTRY="<internal-registry>:443"
PIP_CONF=".pip.conf.build"
CA_BUNDLE_FILE=".ca-bundle.build"

CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-}"
CORPORATE_CA_CERT="${CORPORATE_CA_CERT:-/usr/local/share/ca-certificates/cloud-dog.net.ca.crt}"

echo "=========================================="
echo "Docker Build: ${FOLDER}/${CONTAINER}:${VERSION}"
echo "=========================================="

# ── PyPI Configuration ───────────────────────────────────────────
PYPI_URL="${PYPI_URL:-https://pypi.cloud-dog.net/simple/}"
PYPI_USERNAME="${PYPI_USERNAME:-}"
PYPI_PASSWORD="${PYPI_PASSWORD:-}"

if [[ -z "${PYPI_USERNAME}" || -z "${PYPI_PASSWORD}" ]]; then
  if [[ -f /opt/iac/Development/cloud-dog-ai/env-vault ]]; then
    set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
    VAULT_JSON=$(curl -fsS \
      -H "X-Vault-Token: ${VAULT_TOKEN}" \
      "${VAULT_ADDR}/v1/${VAULT_MOUNT_POINT}/data/${VAULT_CONFIG_PATH}" 2>/dev/null || echo "{}")
    readarray -t PYPI_CREDS < <(VAULT_JSON_PAYLOAD="${VAULT_JSON}" python3 - <<'PY'
import json, os
raw = os.environ.get("VAULT_JSON_PAYLOAD", "{}")
payload = json.loads(raw).get("data", {}).get("data", {})
if isinstance(payload.get("json"), dict):
    dev = payload["json"].get("dev", {})
elif isinstance(payload.get("json"), str):
    dev = json.loads(payload["json"]).get("dev", {})
elif isinstance(payload.get("content"), str):
    dev = json.loads(payload["content"]).get("dev", {})
else:
    dev = payload.get("dev", {}) if isinstance(payload, dict) else {}
repo = dev.get("repository", {}) if isinstance(dev, dict) else {}
pypi = repo.get("pypi", {}) if isinstance(repo, dict) else {}
print(pypi.get("username", ""))
print(pypi.get("password", ""))
PY
    ) || true
    PYPI_USERNAME="${PYPI_CREDS[0]:-}"
    PYPI_PASSWORD="${PYPI_CREDS[1]:-}"
  fi
fi

if [[ -n "${PYPI_USERNAME}" ]] && [[ -n "${PYPI_PASSWORD}" ]]; then
  cat > "${PIP_CONF}" << EOF
[global]
extra-index-url = https://${PYPI_USERNAME}:${PYPI_PASSWORD}@${PYPI_URL#https://}
trusted-host = $(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'gitea.cloud-dog.net')")
               pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf: authenticated PyPI access."
else
  cat > "${PIP_CONF}" << EOF
[global]
extra-index-url = ${PYPI_URL}
trusted-host = $(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'gitea.cloud-dog.net')")
               pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf: anonymous PyPI access."
fi
chmod 600 "${PIP_CONF}"

# ── CA Certificate ───────────────────────────────────────────────
rm -f "${CA_BUNDLE_FILE}"
touch "${CA_BUNDLE_FILE}"
for cert in "${CUSTOM_CA_CERT}" "${CORPORATE_CA_CERT}"; do
  if [[ -n "${cert}" && -f "${cert}" ]]; then
    cat "${cert}" >> "${CA_BUNDLE_FILE}"
    echo "" >> "${CA_BUNDLE_FILE}"
  fi
done
chmod 600 "${CA_BUNDLE_FILE}"

# ── Build ────────────────────────────────────────────────────────
DOCKER_BUILDKIT=1 docker buildx build \
  --progress=plain \
  --network=host \
  --load \
  -f Dockerfile \
  --secret id=pip_conf,src="${PIP_CONF}" \
  --secret id=ca_bundle,src="${CA_BUNDLE_FILE}" \
  --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --build-arg NO_PROXY="${NO_PROXY:-}" \
  --build-arg http_proxy="${http_proxy:-}" \
  --build-arg https_proxy="${https_proxy:-}" \
  --build-arg no_proxy="${no_proxy:-}" \
  -t "${FOLDER}/${CONTAINER}:${VERSION}" \
  . 2>&1 | tee docker-build.log

BUILD_STATUS=${PIPESTATUS[0]}

if [[ ${BUILD_STATUS} -eq 0 ]]; then
  echo "Build OK: ${FOLDER}/${CONTAINER}:${VERSION}"
  docker tag "${FOLDER}/${CONTAINER}:${VERSION}" \
    "${REGISTRY}/${FOLDER}/${CONTAINER}:${VERSION}"
else
  echo "Build FAILED"
fi

rm -f "${PIP_CONF}" "${CA_BUNDLE_FILE}"
exit ${BUILD_STATUS}
