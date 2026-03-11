from __future__ import annotations

from tests.env_runtime import env_get, runtime_env

from contextlib import contextmanager
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit
from urllib.request import urlopen


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _normalize_path(path: str | None, *, default: str) -> str:
    if not path:
        return default
    cleaned = path.strip()
    if not cleaned:
        return default
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    if len(cleaned) > 1 and cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/")
    return cleaned or "/"


def _join_paths(base_path: str, path: str) -> str:
    base = _normalize_path(base_path, default="/")
    sub = _normalize_path(path, default="/")
    if base == "/":
        return sub
    if sub == "/":
        return base
    if sub == base or sub.startswith(f"{base}/"):
        return sub
    return f"{base}{sub}"


def _canonical_health_url(url: str) -> str:
    parsed = urlsplit(url)
    api_base = _normalize_path(env_get("TEST_API_BASE_PATH"), default="/app/v1")
    canonical_path = _join_paths(api_base, parsed.path or "/health")
    canonical_parts = SplitResult(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=canonical_path,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(canonical_parts)


def wait_for_health(url: str, timeout_s: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout_s
    candidates = [url]
    canonical_url = _canonical_health_url(url)
    if canonical_url != url:
        candidates.insert(0, canonical_url)
    while time.monotonic() < deadline:
        for probe_url in candidates:
            try:
                with urlopen(probe_url, timeout=0.5) as response:
                    if response.status == 200:
                        return json.loads(response.read().decode("utf-8"))
            except Exception:
                continue
        time.sleep(0.1)
    raise RuntimeError(f"Health check timed out: {candidates}")


def write_server_config(
    base_dir: Path,
    *,
    port: int,
    root_dir: Path,
    api_keys: list[str] | None = None,
    allow_globs: list[str] | None = None,
    deny_globs: list[str] | None = None,
    auth_header_name: str = "Authorization",
    auth_header_scheme: str = "Bearer",
    search_max_results: int = 25,
    search_max_file_mb: int = 2,
    search_timeout_s: int = 10,
    conversion_timeout_s: int = 10,
    conversion_max_input_mb: int = 25,
    snapshot_mode: str = "on_change",
    snapshot_retention_days: int = 30,
    snapshot_retention_count: int | None = None,
    snapshot_max_storage_mb: int | None = None,
    validation_default_mode: str = "warn",
    validation_per_type: dict[str, str] | None = None,
    extra_env_lines: list[str] | None = None,
) -> tuple[Path, Path, Path, Path, Path]:
    defaults_path = base_dir / "defaults.yaml"
    config_path = base_dir / "config.yaml"
    env_path = base_dir / "env"
    pidfile = base_dir / "server.pid"
    server_log = base_dir / "server.log"
    audit_log = base_dir / "audit.log.jsonl"
    snapshot_dir = base_dir / "snapshots"

    allow_globs = allow_globs or ["**/*"]
    deny_globs = deny_globs or []
    api_keys = api_keys or ["secret"]
    validation_per_type = validation_per_type or {}

    allow_globs_yaml = "\n".join(f'        - "{item}"' for item in allow_globs)
    deny_globs_yaml = (
        "\n".join(f'        - "{item}"' for item in deny_globs)
        if deny_globs
        else "        []"
    )
    api_keys_yaml = "\n".join(
        f'        - "${{FILE_MCP_API_KEY_{index}}}"'
        for index, _ in enumerate(api_keys, start=1)
    )
    validation_per_type_yaml = (
        "\n".join(
            f'        {key}: "{value}"' for key, value in validation_per_type.items()
        )
        if validation_per_type
        else "        {}"
    )

    defaults_yaml = f"""
profiles:
  default:
    auth:
      api_keys:
{api_keys_yaml}
      header_name: "${{FILE_MCP_AUTH_HEADER_NAME}}"
      header_scheme: "${{FILE_MCP_AUTH_HEADER_SCHEME}}"
    storage:
      backend: "${{FILE_MCP_STORAGE_BACKEND}}"
      tls:
        insecure_skip_verify: "${{FILE_MCP_STORAGE_TLS_INSECURE}}"
        ca_bundle_path: "${{FILE_MCP_STORAGE_TLS_CA_BUNDLE}}"
      s3:
        endpoint: "${{FILE_MCP_S3_ENDPOINT}}"
        bucket: "${{FILE_MCP_S3_BUCKET}}"
        region: "${{FILE_MCP_S3_REGION}}"
        access_key: "${{FILE_MCP_S3_ACCESS_KEY}}"
        secret_key: "${{FILE_MCP_S3_SECRET_KEY}}"
        prefix: "${{FILE_MCP_S3_PREFIX}}"
      webdav:
        base_url: "${{FILE_MCP_WEBDAV_BASE_URL}}"
        username: "${{FILE_MCP_WEBDAV_USERNAME}}"
        password: "${{FILE_MCP_WEBDAV_PASSWORD}}"
      ftp:
        host: "${{FILE_MCP_FTP_HOST}}"
        port: "${{FILE_MCP_FTP_PORT}}"
        username: "${{FILE_MCP_FTP_USERNAME}}"
        password: "${{FILE_MCP_FTP_PASSWORD}}"
        base_dir: "${{FILE_MCP_FTP_BASE_DIR}}"
        use_tls: "${{FILE_MCP_FTP_USE_TLS}}"
    scope:
      roots:
        - "${{FILE_MCP_ROOT}}"
      allow_globs:
{allow_globs_yaml}
      deny_globs:
{deny_globs_yaml}
      allowed_exts: []
      read_only_exts: []
    audit:
      log_path: "${{FILE_MCP_AUDIT_LOG}}"
      include_content_hashes: true
    snapshots:
      enabled: true
      mode: "{snapshot_mode}"
      dir: "${{FILE_MCP_SNAPSHOT_DIR}}"
      retention_days: ${{FILE_MCP_SNAPSHOT_RETENTION_DAYS}}
      retention_count: ${{FILE_MCP_SNAPSHOT_RETENTION_COUNT}}
      max_storage_mb: ${{FILE_MCP_SNAPSHOT_MAX_STORAGE_MB}}
    validation:
      default_mode: "{validation_default_mode}"
      per_type:
{validation_per_type_yaml}
    observability:
      enabled: true
      log_path: "${{FILE_MCP_SERVER_LOG}}"
      level: "INFO"
    limits:
      search_max_results: ${{FILE_MCP_SEARCH_MAX_RESULTS}}
      search_max_file_mb: ${{FILE_MCP_SEARCH_MAX_FILE_MB}}
      search_timeout_s: ${{FILE_MCP_SEARCH_TIMEOUT_S}}
      storage_timeout_s: ${{FILE_MCP_STORAGE_TIMEOUT_S}}
      conversion_timeout_s: ${{FILE_MCP_CONVERSION_TIMEOUT_S}}
    conversion:
      enabled: true
      backends: []
      max_input_mb: ${{FILE_MCP_CONVERSION_MAX_INPUT_MB}}
http:
  transport: "${{FILE_MCP_HTTP_TRANSPORT}}"
  host: "${{FILE_MCP_HTTP_HOST}}"
  port: "${{FILE_MCP_HTTP_PORT}}"
  base_path: "${{FILE_MCP_HTTP_BASE_PATH}}"
  mcp_path: "${{FILE_MCP_HTTP_MCP_PATH}}"
  health_path: "${{FILE_MCP_HTTP_HEALTH_PATH}}"
  events_path: "${{FILE_MCP_HTTP_EVENTS_PATH}}"
  stateless_http: "${{FILE_MCP_HTTP_STATELESS}}"
""".lstrip()
    defaults_path.write_text(defaults_yaml, encoding="utf-8")
    config_path.write_text(defaults_yaml, encoding="utf-8")
    env_lines = [
        f"FILE_MCP_AUTH_HEADER_NAME={auth_header_name}",
        f"FILE_MCP_AUTH_HEADER_SCHEME={auth_header_scheme}",
        f"FILE_MCP_ROOT={root_dir}",
        f"FILE_MCP_SERVER_LOG={server_log}",
        f"FILE_MCP_AUDIT_LOG={audit_log}",
        f"FILE_MCP_SNAPSHOT_DIR={snapshot_dir}",
        "FILE_MCP_HTTP_TRANSPORT=streamable-http",
        "FILE_MCP_HTTP_HOST=127.0.0.1",
        f"FILE_MCP_HTTP_PORT={port}",
        f"FILE_MCP_HTTP_BASE_PATH={_normalize_path(env_get('TEST_API_BASE_PATH'), default='/app/v1')}",
        f"FILE_MCP_HTTP_MCP_PATH={_normalize_path(env_get('TEST_MCP_BASE_PATH'), default='/mcp')}",
        "FILE_MCP_HTTP_HEALTH_PATH=/health",
        "FILE_MCP_HTTP_EVENTS_PATH=/events",
        "FILE_MCP_HTTP_STATELESS=true",
        f"FILE_MCP_SEARCH_MAX_RESULTS={search_max_results}",
        f"FILE_MCP_SEARCH_MAX_FILE_MB={search_max_file_mb}",
        f"FILE_MCP_SEARCH_TIMEOUT_S={search_timeout_s}",
        "FILE_MCP_STORAGE_BACKEND=local",
        "FILE_MCP_STORAGE_TLS_INSECURE=false",
        "FILE_MCP_STORAGE_TLS_CA_BUNDLE=",
        f"FILE_MCP_STORAGE_TIMEOUT_S={search_timeout_s}",
        "FILE_MCP_S3_ENDPOINT=",
        "FILE_MCP_S3_BUCKET=",
        "FILE_MCP_S3_REGION=",
        "FILE_MCP_S3_ACCESS_KEY=",
        "FILE_MCP_S3_SECRET_KEY=",
        "FILE_MCP_S3_PREFIX=",
        "FILE_MCP_WEBDAV_BASE_URL=",
        "FILE_MCP_WEBDAV_USERNAME=",
        "FILE_MCP_WEBDAV_PASSWORD=",
        "FILE_MCP_FTP_HOST=",
        "FILE_MCP_FTP_PORT=",
        "FILE_MCP_FTP_USERNAME=",
        "FILE_MCP_FTP_PASSWORD=",
        "FILE_MCP_FTP_BASE_DIR=/",
        "FILE_MCP_FTP_USE_TLS=false",
        f"FILE_MCP_CONVERSION_TIMEOUT_S={conversion_timeout_s}",
        f"FILE_MCP_CONVERSION_MAX_INPUT_MB={conversion_max_input_mb}",
        f"FILE_MCP_SNAPSHOT_RETENTION_DAYS={snapshot_retention_days}",
        f"FILE_MCP_SNAPSHOT_RETENTION_COUNT={snapshot_retention_count if snapshot_retention_count is not None else -1}",
        f"FILE_MCP_SNAPSHOT_MAX_STORAGE_MB={snapshot_max_storage_mb if snapshot_max_storage_mb is not None else -1}",
    ]
    if extra_env_lines:
        env_lines.extend(extra_env_lines)
    for index, api_key in enumerate(api_keys, start=1):
        env_lines.insert(index - 1, f"FILE_MCP_API_KEY_{index}={api_key}")
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    return defaults_path, config_path, env_path, pidfile, audit_log


@contextmanager
def running_server(
    repo_root: Path,
    *,
    defaults_path: Path,
    config_path: Path,
    env_path: Path,
    pidfile: Path,
    extra_env: dict[str, str] | None = None,
):
    cmd = [
        sys.executable,
        "-m",
        "file_mcp_server",
        "serve",
        "--profile",
        "default",
        "--env-path",
        str(env_path),
        "--config-path",
        str(config_path),
        "--defaults-path",
        str(defaults_path),
        "--pidfile",
        str(pidfile),
        "--force-pidfile",
    ]
    env = {
        key: value
        for key, value in runtime_env.items()
        if not (key.startswith("FILE_MCP_") or key.startswith("CLOUD_DOG__"))
    }
    env["PYTHONPATH"] = "src"
    if extra_env:
        env.update(extra_env)

    process = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
