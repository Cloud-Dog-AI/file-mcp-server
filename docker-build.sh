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
CLOUD_DOG_SITE_PACKAGES="${CLOUD_DOG_SITE_PACKAGES:-}"
CLOUD_DOG_CONFIG_SRC="${CLOUD_DOG_CONFIG_SRC:-}"
CLOUD_DOG_LOGGING_SRC="${CLOUD_DOG_LOGGING_SRC:-}"
CLOUD_DOG_DB_SRC="${CLOUD_DOG_DB_SRC:-}"
CLOUD_DOG_JOBS_SRC="${CLOUD_DOG_JOBS_SRC:-}"

if [[ -z "${CLOUD_DOG_SITE_PACKAGES}" ]]; then
  CLOUD_DOG_SITE_PACKAGES="$(find .venv/lib -maxdepth 2 -type d -name site-packages 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${CLOUD_DOG_SITE_PACKAGES}" || ! -d "${CLOUD_DOG_SITE_PACKAGES}" ]]; then
  echo "Unable to locate local site-packages for cloud_dog_* package injection."
  echo "Set CLOUD_DOG_SITE_PACKAGES=<path> and re-run."
  exit 1
fi

if [[ -z "${CLOUD_DOG_CONFIG_SRC}" && -f "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_config.pth" ]]; then
  CLOUD_DOG_CONFIG_SRC="$(head -n 1 "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_config.pth" | tr -d '\r')"
fi

if [[ -z "${CLOUD_DOG_LOGGING_SRC}" && -f "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_logging.pth" ]]; then
  CLOUD_DOG_LOGGING_SRC="$(head -n 1 "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_logging.pth" | tr -d '\r')"
fi

if [[ -z "${CLOUD_DOG_DB_SRC}" && -f "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_db.pth" ]]; then
  CLOUD_DOG_DB_SRC="$(head -n 1 "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_db.pth" | tr -d '\r')"
fi

if [[ -z "${CLOUD_DOG_JOBS_SRC}" && -f "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_jobs.pth" ]]; then
  CLOUD_DOG_JOBS_SRC="$(head -n 1 "${CLOUD_DOG_SITE_PACKAGES}/_cloud_dog_jobs.pth" | tr -d '\r')"
fi

if [[ ! -d "${CLOUD_DOG_CONFIG_SRC}/cloud_dog_config" ]]; then
  echo "Unable to locate cloud_dog_config source: ${CLOUD_DOG_CONFIG_SRC:-<unset>}"
  echo "Set CLOUD_DOG_CONFIG_SRC=<path> and re-run."
  exit 1
fi

if [[ ! -d "${CLOUD_DOG_LOGGING_SRC}/cloud_dog_logging" ]]; then
  echo "Unable to locate cloud_dog_logging source: ${CLOUD_DOG_LOGGING_SRC:-<unset>}"
  echo "Set CLOUD_DOG_LOGGING_SRC=<path> and re-run."
  exit 1
fi

if [[ ! -d "${CLOUD_DOG_DB_SRC}/cloud_dog_db" ]]; then
  echo "Unable to locate cloud_dog_db source: ${CLOUD_DOG_DB_SRC:-<unset>}"
  echo "Set CLOUD_DOG_DB_SRC=<path> and re-run."
  exit 1
fi

if [[ ! -d "${CLOUD_DOG_JOBS_SRC}/cloud_dog_jobs" ]]; then
  echo "Unable to locate cloud_dog_jobs source: ${CLOUD_DOG_JOBS_SRC:-<unset>}"
  echo "Set CLOUD_DOG_JOBS_SRC=<path> and re-run."
  exit 1
fi

echo "=========================================="
echo "Docker Build"
echo "=========================================="
echo "Image: ${IMAGE_NAME}"
echo "Proxy: ${HTTP_PROXY:-<none>}"
echo "CA Cert: ${CUSTOM_CA_CERT:-<none>}"
echo "Cloud packages: ${CLOUD_DOG_SITE_PACKAGES}"
echo "cloud_dog_config src: ${CLOUD_DOG_CONFIG_SRC}"
echo "cloud_dog_logging src: ${CLOUD_DOG_LOGGING_SRC}"
echo "cloud_dog_db src: ${CLOUD_DOG_DB_SRC}"
echo "cloud_dog_jobs src: ${CLOUD_DOG_JOBS_SRC}"
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
  --build-context cloud_dog_site_packages="${CLOUD_DOG_SITE_PACKAGES}" \
  --build-context cloud_dog_config_src="${CLOUD_DOG_CONFIG_SRC}" \
  --build-context cloud_dog_logging_src="${CLOUD_DOG_LOGGING_SRC}" \
  --build-context cloud_dog_db_src="${CLOUD_DOG_DB_SRC}" \
  --build-context cloud_dog_jobs_src="${CLOUD_DOG_JOBS_SRC}" \
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
