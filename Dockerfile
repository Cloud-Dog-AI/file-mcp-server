# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.
# file-mcp-server container image

FROM python:3.12-slim AS builder

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}
ENV no_proxy=${no_proxy}

WORKDIR /app

ARG CUSTOM_CA_CERT
RUN set -e; \
    if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      gcc \
      libxml2-dev \
      libxslt1-dev \
      libmagic1 \
      libmagic-dev \
      curl; \
    rm -rf /var/lib/apt/lists/*

COPY REQUIREMENTS.txt ./REQUIREMENTS.txt
# Install platform packages from the internal package index per §3.2.0, then remaining deps from REQUIREMENTS.
ARG PYPI_URL=https://pypi.cloud-dog.net/simple
ARG PYPI_TRUSTED_HOST=pypi.cloud-dog.net
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir \
      --extra-index-url ${PYPI_URL} \
      --trusted-host ${PYPI_TRUSTED_HOST} \
      --trusted-host files.pythonhosted.org \
      "cloud-dog-config==0.3.4" \
      cloud-dog-logging \
      "cloud-dog-api-kit[change-stream-db]>=0.14.0" \
      "cloud-dog-idam==0.5.3" \
      "cloud-dog-llm==0.4.0" \
      "cloud-dog-db>=0.2.0" \
      cloud-dog-jobs \
      cloud-dog-storage
RUN grep -v '^cloud_dog_' REQUIREMENTS.txt > /tmp/REQUIREMENTS.docker.txt && \
    pip install --no-cache-dir -r /tmp/REQUIREMENTS.docker.txt && \
    pip install --no-cache-dir 'redis>=5.0'

FROM python:3.12-slim
ARG SOURCE_COMMIT=unknown
ARG SOURCE_BRANCH=unknown
# W28E-1863 fix-wave-b (WSC-014): build timestamp for build-identity provenance.
ARG BUILD_DATE=""
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.vendor="Cloud-Dog, Viewdeck Engineering Limited"
LABEL org.opencontainers.image.revision="${SOURCE_COMMIT}"
LABEL org.opencontainers.image.ref.name="${SOURCE_BRANCH}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"

# W28E-1863 fix-wave-b (WSC-014): surface build identity to the RUNTIME so the
# server's _build_identity() (read config-routed via read_env_var, RULES §1.4.1)
# can populate /version + /runtime-config.js for the WebUI About page.
ENV FILE_MCP_SOURCE_COMMIT=${SOURCE_COMMIT}
ENV FILE_MCP_SOURCE_BRANCH=${SOURCE_BRANCH}
ENV FILE_MCP_BUILD_DATE=${BUILD_DATE}

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}
ENV no_proxy=${no_proxy}

WORKDIR /app

ARG CUSTOM_CA_CERT
RUN set -e; \
    if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      curl \
      netcat-openbsd \
      procps \
      net-tools \
      libmagic1 \
      pandoc; \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src ./src
COPY scripts ./scripts
COPY pyproject.toml ./pyproject.toml
COPY server_control.sh ./server_control.sh
COPY defaults.yaml ./defaults.yaml
COPY config.yaml ./config.yaml
COPY README.md ./README.md
COPY LICENSE ./LICENSE
COPY docker-env.example ./docker-env.example
COPY env-docker-defaults ./env-docker-defaults
COPY docker-entrypoint.sh ./docker-entrypoint.sh
COPY healthcheck.sh ./healthcheck.sh
COPY DOCKER-README.me ./DOCKER-README.me
COPY certs ./certs
COPY database ./database
COPY ui ./ui

RUN mkdir -p /app/.run /app/logs /app/certs /app/storage /app/tmp /app/archive
RUN chmod +x /app/docker-entrypoint.sh /app/healthcheck.sh /app/server_control.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV FILE_MCP_HEALTH_HOST=127.0.0.1
ENV FILE_MCP_HEALTH_PATH=/health

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD /app/healthcheck.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["serve"]
