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

IMAGE_NAME="${1:-cloud-dog/file-mcp-server:latest}"
CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-}"
GENERIC_CA_CERT="custom-ca.crt"
CERT_ARG=""
# Cloud-dog packages installed from Gitea PyPI during docker build (no local source needed)

echo "=========================================="
echo "Docker Build"
echo "=========================================="
echo "Image: ${IMAGE_NAME}"
echo "Proxy: ${HTTP_PROXY:-<none>}"
echo "CA Cert: ${CUSTOM_CA_CERT:-<none>}"
echo "Cloud packages: from Gitea PyPI"
echo "Build mode: Gitea PyPI (no local source injection)"
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
