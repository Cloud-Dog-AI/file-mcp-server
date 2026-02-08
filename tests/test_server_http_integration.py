from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(url: str, timeout_s: float = 10.0) -> dict:
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


def test_http_health_and_authenticated_tool_call(tmp_path: Path) -> None:
    port = _pick_free_port()
    defaults_path = tmp_path / "defaults.yaml"
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / "env"
    pidfile = tmp_path / "server.pid"
    server_log = tmp_path / "server.log"
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "hello.txt"
    target.write_text("hello over http", encoding="utf-8")

    defaults_yaml = """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
      header_name: "${FILE_MCP_AUTH_HEADER_NAME}"
      header_scheme: "${FILE_MCP_AUTH_HEADER_SCHEME}"
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
      allow_globs:
        - "**/*"
      deny_globs: []
      allowed_exts: []
      read_only_exts: []
    validation:
      default_mode: "warn"
      per_type: {}
    observability:
      enabled: true
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "INFO"
    limits:
      search_max_results: 25
      search_max_file_mb: 2
      conversion_timeout_s: 10
http:
  transport: "${FILE_MCP_HTTP_TRANSPORT}"
  host: "${FILE_MCP_HTTP_HOST}"
  port: "${FILE_MCP_HTTP_PORT}"
  base_path: "${FILE_MCP_HTTP_BASE_PATH}"
  mcp_path: "${FILE_MCP_HTTP_MCP_PATH}"
  health_path: "${FILE_MCP_HTTP_HEALTH_PATH}"
  events_path: "${FILE_MCP_HTTP_EVENTS_PATH}"
  stateless_http: "${FILE_MCP_HTTP_STATELESS}"
""".lstrip()
    defaults_path.write_text(defaults_yaml, encoding="utf-8")
    config_path.write_text(defaults_yaml, encoding="utf-8")
    env_path.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_PRIMARY=secret",
                "FILE_MCP_AUTH_HEADER_NAME=Authorization",
                "FILE_MCP_AUTH_HEADER_SCHEME=Bearer",
                f"FILE_MCP_ROOT={root_dir}",
                f"FILE_MCP_SERVER_LOG={server_log}",
                "FILE_MCP_HTTP_TRANSPORT=streamable-http",
                "FILE_MCP_HTTP_HOST=127.0.0.1",
                f"FILE_MCP_HTTP_PORT={port}",
                "FILE_MCP_HTTP_BASE_PATH=/",
                "FILE_MCP_HTTP_MCP_PATH=/mcp",
                "FILE_MCP_HTTP_HEALTH_PATH=/health",
                "FILE_MCP_HTTP_EVENTS_PATH=/events",
                "FILE_MCP_HTTP_STATELESS=true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[1]
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

    process = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        health = _wait_for_health(f"http://127.0.0.1:{port}/health")
        assert health["status"] == "ok"
        assert health["service"] == "file-mcp-server"

        async def _call_read_file() -> str:
            transport = StreamableHttpTransport(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer secret"},
            )
            async with Client(transport) as client:
                tools = await client.list_tools()
                assert any(tool.name == "read_file" for tool in tools)
                result = await client.call_tool("read_file", {"path": str(target)})
                text_blocks = [item.text for item in result.content if hasattr(item, "text")]
                return "\n".join(text_blocks)

        response_text = asyncio.run(_call_read_file())
        assert "hello over http" in response_text
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
