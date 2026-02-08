from __future__ import annotations

from contextlib import contextmanager
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(url: str, timeout_s: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except Exception:
            time.sleep(0.1)
            continue
    raise RuntimeError(f"Health check timed out: {url}")


def write_server_config(
    base_dir: Path,
    *,
    port: int,
    root_dir: Path,
    allow_globs: list[str] | None = None,
    deny_globs: list[str] | None = None,
    auth_header_name: str = "Authorization",
    auth_header_scheme: str = "Bearer",
    search_max_results: int = 25,
    search_max_file_mb: int = 2,
    conversion_timeout_s: int = 10,
    conversion_max_input_mb: int = 25,
    snapshot_mode: str = "on_change",
    snapshot_retention_days: int = 30,
    snapshot_retention_count: int | None = None,
    snapshot_max_storage_mb: int | None = None,
    validation_default_mode: str = "warn",
    validation_per_type: dict[str, str] | None = None,
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
    validation_per_type = validation_per_type or {}

    allow_globs_yaml = "\n".join(f'        - "{item}"' for item in allow_globs)
    deny_globs_yaml = "\n".join(f'        - "{item}"' for item in deny_globs) if deny_globs else "        []"
    validation_per_type_yaml = (
        "\n".join(f'        {key}: "{value}"' for key, value in validation_per_type.items())
        if validation_per_type
        else "        {}"
    )

    defaults_yaml = f"""
profiles:
  default:
    auth:
      api_keys:
        - "${{FILE_MCP_API_KEY_PRIMARY}}"
      header_name: "${{FILE_MCP_AUTH_HEADER_NAME}}"
      header_scheme: "${{FILE_MCP_AUTH_HEADER_SCHEME}}"
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
    env_path.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_PRIMARY=secret",
                f"FILE_MCP_AUTH_HEADER_NAME={auth_header_name}",
                f"FILE_MCP_AUTH_HEADER_SCHEME={auth_header_scheme}",
                f"FILE_MCP_ROOT={root_dir}",
                f"FILE_MCP_SERVER_LOG={server_log}",
                f"FILE_MCP_AUDIT_LOG={audit_log}",
                f"FILE_MCP_SNAPSHOT_DIR={snapshot_dir}",
                "FILE_MCP_HTTP_TRANSPORT=streamable-http",
                "FILE_MCP_HTTP_HOST=127.0.0.1",
                f"FILE_MCP_HTTP_PORT={port}",
                "FILE_MCP_HTTP_BASE_PATH=/",
                "FILE_MCP_HTTP_MCP_PATH=/mcp",
                "FILE_MCP_HTTP_HEALTH_PATH=/health",
                "FILE_MCP_HTTP_EVENTS_PATH=/events",
                "FILE_MCP_HTTP_STATELESS=true",
                f"FILE_MCP_SEARCH_MAX_RESULTS={search_max_results}",
                f"FILE_MCP_SEARCH_MAX_FILE_MB={search_max_file_mb}",
                f"FILE_MCP_CONVERSION_TIMEOUT_S={conversion_timeout_s}",
                f"FILE_MCP_CONVERSION_MAX_INPUT_MB={conversion_max_input_mb}",
                f"FILE_MCP_SNAPSHOT_RETENTION_DAYS={snapshot_retention_days}",
                f"FILE_MCP_SNAPSHOT_RETENTION_COUNT={snapshot_retention_count if snapshot_retention_count is not None else -1}",
                f"FILE_MCP_SNAPSHOT_MAX_STORAGE_MB={snapshot_max_storage_mb if snapshot_max_storage_mb is not None else -1}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
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
    env = dict(os.environ)
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
