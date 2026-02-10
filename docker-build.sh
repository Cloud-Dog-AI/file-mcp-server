#!/usr/bin/env bash
# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

set -euo pipefail

IMAGE_NAME="${1:-cloud-dog/file-mcp-server:latest}"
CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-}"
GENERIC_CA_CERT="custom-ca.crt"
CERT_ARG=""

echo "=========================================="
echo "Docker Build"
echo "=========================================="
echo "Image: ${IMAGE_NAME}"
echo "Proxy: ${HTTP_PROXY:-<none>}"
echo "CA Cert: ${CUSTOM_CA_CERT:-<none>}"
echo "=========================================="

if [[ -n "${CUSTOM_CA_CERT}" && -f "${CUSTOM_CA_CERT}" ]]; then
  cp "${CUSTOM_CA_CERT}" "./${GENERIC_CA_CERT}"
  CERT_ARG="--build-arg CUSTOM_CA_CERT=./${GENERIC_CA_CERT}"
fi

# shellcheck disable=SC2086

docker buildx build \
  --progress=plain \
  --network=host \
  --load \
  -f Dockerfile \
  ${CERT_ARG} \
  --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --build-arg NO_PROXY="${NO_PROXY:-}" \
  --build-arg http_proxy="${http_proxy:-}" \
  --build-arg https_proxy="${https_proxy:-}" \
  --build-arg no_proxy="${no_proxy:-}" \
  -t "${IMAGE_NAME}" \
  . | tee docker-build.log

if [[ -f "./${GENERIC_CA_CERT}" ]]; then
  rm -f "./${GENERIC_CA_CERT}"
fi

echo "Build complete: ${IMAGE_NAME}"
