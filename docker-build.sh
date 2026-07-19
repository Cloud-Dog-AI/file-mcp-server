#!/usr/bin/env bash
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

# file-mcp-server — Docker Build Script (PS-91 / PS-97 v1.1 §1.1.3)
# Uses a BuildKit secret mount for PyPI auth — credentials never enter build args
# or image layers.
# Pattern: identical to git-mcp-server (the reference).
#
# Variant selector (PS-97 v1.1 §1.1.3):
#   --variant public  (default) builds Dockerfile.public for publication.
#                      Single public index (PYPI_URL defaults to pypi.org),
#                      no --extra-index-url, no internal-host default (W28A-861-R3 §4).
#   --variant dev      builds the internal Dockerfile (Gitea/internal package
#                      index default) for developer checkouts.
#
# Usage:
#   docker-build.sh [VERSION] [--variant dev|public]
set -euo pipefail

require_main_or_release_branch() {
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  # Publication-suffixed artifacts are local verification builds; the suffix
  # path suppresses registry tagging, so it is safe from a repair branch.
  if [[ -n "${PUBLICATION_TAG_SUFFIX:-}" ]]; then
    return 0
  fi
  case "${branch}" in
    main|release/*)
      return 0
      ;;
  esac

  echo "ERROR: docker-build.sh refuses to build/push from non-main branch. Got '${branch:-unknown}'; checkout main or release/*." >&2
  exit 1
}

require_main_or_release_branch

# ── Argument parsing ────────────────────────────────────────────
VARIANT="${PUBLICATION_BUILD_VARIANT:-public}"
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant)
      VARIANT="${2:-dev}"
      shift 2
      ;;
    --variant=*)
      VARIANT="${1#*=}"
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

case "${VARIANT}" in
  dev)
    DOCKERFILE="Dockerfile"
    ;;
  public)
    DOCKERFILE="Dockerfile.public"
    ;;
  *)
    echo "ERROR: --variant must be 'dev' or 'public' (got: ${VARIANT})" >&2
    exit 2
    ;;
esac
if [[ ! -f "${DOCKERFILE}" ]]; then
  echo "ERROR: ${DOCKERFILE} not found (variant=${VARIANT})" >&2
  exit 2
fi

VERSION="${1:-latest}"
CONTAINER="file-mcp-server"
FOLDER="cloud-dog"
REGISTRY="${REGISTRY:-}"
SOURCE_COMMIT="$(git rev-parse HEAD)"
SOURCE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
# W28E-1863 fix-wave-b (WSC-014): build timestamp for build-identity provenance.
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PIP_CONF=".pip.conf.build"
CA_BUNDLE_FILE=".ca-bundle.build"

PUBLICATION_TAG_SUFFIX="${PUBLICATION_TAG_SUFFIX:-}"
if [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
  if [[ ! "${PUBLICATION_TAG_SUFFIX}" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    echo "ERROR: PUBLICATION_TAG_SUFFIX must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?\$ (got: '${PUBLICATION_TAG_SUFFIX}')" >&2
    exit 2
  fi
  case "${PUBLICATION_TAG_SUFFIX}" in
    latest|dev|prod|release|stable)
      echo "ERROR: PUBLICATION_TAG_SUFFIX '${PUBLICATION_TAG_SUFFIX}' is reserved" >&2
      exit 2
      ;;
  esac
  EFFECTIVE_TAG="${VERSION}-${PUBLICATION_TAG_SUFFIX}"
  echo "Publication test build: tag suffix '-${PUBLICATION_TAG_SUFFIX}' (registry tag will be skipped)."
else
  EFFECTIVE_TAG="${VERSION}"
fi

CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-}"
CORPORATE_CA_CERT="${CORPORATE_CA_CERT:-/usr/local/share/ca-certificates/cloud-dog.net.ca.crt}"

echo "=========================================="
echo "Docker Build: ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG} (variant=${VARIANT}, dockerfile=${DOCKERFILE})"
echo "=========================================="

# ── PyPI Configuration ───────────────────────────────────────────
# Default index depends on variant:
#   public → public PyPI (single index, no extra-index-url; PS-97 §3.3 / §4).
#   dev    → caller-supplied approved development index.
if [[ -n "${PYPI_URL:-}" ]]; then
  : # honour caller override
elif [[ "${VARIANT}" == "public" ]]; then
  PYPI_URL="https://pypi.org/simple"
else
  echo "ERROR: --variant dev requires an explicit PYPI_URL" >&2
  exit 2
fi
PYPI_USERNAME="${PYPI_USERNAME:-}"
PYPI_PASSWORD="${PYPI_PASSWORD:-}"

# Vault stores the internal registry as its canonical root URL. pip requires the
# PEP 503 simple endpoint, so normalise that one approved internal host here.
PYPI_URL="$(python3 - "${PYPI_URL}" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

url = sys.argv[1]
parts = urlsplit(url)
if parts.hostname and parts.hostname.endswith("pypi.cloud-dog.net"):
    path = parts.path.rstrip("/")
    if not path:
        url = urlunsplit((parts.scheme, parts.netloc, "/simple/", parts.query, parts.fragment))
    elif path != "/simple" and not path.endswith("/simple"):
        url = urlunsplit((parts.scheme, parts.netloc, f"{path}/simple/", parts.query, parts.fragment))
    elif not parts.path.endswith("/"):
        url = urlunsplit((parts.scheme, parts.netloc, f"{path}/", parts.query, parts.fragment))
print(url)
PY
)"

PYPI_HOST="$(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'pypi.org')")"

if [[ "${VARIANT}" == "public" ]]; then
  # Single strict index — no extra-index-url (PS-97 §3.3 / §4).
  if [[ -n "${PYPI_USERNAME}" ]] || [[ -n "${PYPI_PASSWORD}" ]]; then
    echo "ERROR: use an external pip auth helper; credentials must not be embedded in index URLs" >&2
    exit 2
  else
    cat > "${PIP_CONF}" << EOF
[global]
index-url = ${PYPI_URL}
trusted-host = ${PYPI_HOST}
EOF
    echo "pip.conf: public variant, anonymous single-index access (${PYPI_HOST})."
  fi
else
  # Dev variant uses the explicit caller-selected single index.
  if [[ -n "${PYPI_USERNAME}" ]] || [[ -n "${PYPI_PASSWORD}" ]]; then
    if [[ -z "${PYPI_USERNAME}" ]] || [[ -z "${PYPI_PASSWORD}" ]]; then
      echo "ERROR: dev index authentication requires both PYPI_USERNAME and PYPI_PASSWORD" >&2
      exit 2
    fi
    PIP_AUTH_URL="$(
      PYPI_BASE_URL="${PYPI_URL}" \
      PYPI_AUTH_USERNAME="${PYPI_USERNAME}" \
      PYPI_AUTH_PASSWORD="${PYPI_PASSWORD}" \
      python3 - <<'PY'
import os
from urllib.parse import quote, urlsplit, urlunsplit

parts = urlsplit(os.environ["PYPI_BASE_URL"])
if not parts.hostname:
    raise SystemExit("PYPI_URL must include a hostname")
username = quote(os.environ["PYPI_AUTH_USERNAME"], safe="")
password = quote(os.environ["PYPI_AUTH_PASSWORD"], safe="")
host = parts.hostname
if parts.port is not None:
    host = f"{host}:{parts.port}"
print(urlunsplit((parts.scheme, f"{username}:{password}@{host}", parts.path, parts.query, parts.fragment)))
PY
    )"
    cat > "${PIP_CONF}" << EOF
[global]
index-url = ${PIP_AUTH_URL}
trusted-host = ${PYPI_HOST}
EOF
    unset PIP_AUTH_URL
    echo "pip.conf: dev variant, authenticated single-index secret (${PYPI_HOST})."
  else
    cat > "${PIP_CONF}" << EOF
[global]
index-url = ${PYPI_URL}
trusted-host = ${PYPI_HOST}
EOF
    echo "pip.conf: dev variant, anonymous single-index access (${PYPI_HOST})."
  fi
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
# ── W28C-1719 publish-before-pin guard + build-provenance revision label (fail-closed) ──
_PBP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
"${_PBP_DIR}/scripts/publish-before-pin-guard.sh" "${_PBP_DIR}" || exit $?
_PBP_REV="$(git -C "${_PBP_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"

DOCKER_BUILDKIT=1 docker buildx build \
  --label "org.opencontainers.image.revision=${_PBP_REV}" \
  --progress=plain \
  --network=host \
  --load \
  -f "${DOCKERFILE}" \
  --secret id=pip_conf,src="${PIP_CONF}" \
  --secret id=ca_bundle,src="${CA_BUNDLE_FILE}" \
  --build-arg PYPI_INDEX_URL="${PYPI_URL}" \
  --build-arg PYPI_URL="${PYPI_URL}" \
  --build-arg SOURCE_COMMIT="${SOURCE_COMMIT}" \
  --build-arg SOURCE_BRANCH="${SOURCE_BRANCH}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --build-arg NO_PROXY="${NO_PROXY:-}" \
  --build-arg http_proxy="${http_proxy:-}" \
  --build-arg https_proxy="${https_proxy:-}" \
  --build-arg no_proxy="${no_proxy:-}" \
  -t "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
  . 2>&1 | tee docker-build.log

BUILD_STATUS=${PIPESTATUS[0]}

if [[ ${BUILD_STATUS} -eq 0 ]]; then
  echo "Build OK: ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG} (variant=${VARIANT})"
  if [[ "${VARIANT}" == "dev" && -n "${REGISTRY}" && -z "${PUBLICATION_TAG_SUFFIX}" ]]; then
    docker tag "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
      "${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
    echo "Tagged: ${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  elif [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "Registry tag skipped for publication suffix '${PUBLICATION_TAG_SUFFIX}'."
  else
    echo "Registry tag skipped (public variant or no REGISTRY set; PS-97 §1.1.3 closed-loop)."
  fi
else
  echo "Build FAILED — see docker-build.log"
fi

rm -f "${PIP_CONF}" "${CA_BUNDLE_FILE}"
exit ${BUILD_STATUS}
