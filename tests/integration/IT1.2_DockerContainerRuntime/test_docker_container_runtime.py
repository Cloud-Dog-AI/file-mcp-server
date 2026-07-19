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

"""Docker container runtime tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Validate file-mcp-server container build/run behavior and network modes.
"""

from __future__ import annotations

from tests.env_runtime import env_get, runtime_env
from tests.docker_test_image import require_dev_docker_test_image

import asyncio
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path
from tests.path_helpers import project_root
from urllib.request import urlopen

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(url: str, timeout_s: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=0.75) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except Exception:
            time.sleep(0.2)
            continue
    raise RuntimeError(f"Health check timed out: {url}")


def _docker_cmd(*args: str) -> list[str]:
    docker_host = env_get("FILE_MCP_DOCKER_HOST", "").strip()
    cmd = ["docker"]
    if docker_host:
        cmd.extend(["-H", docker_host])
    cmd.extend(args)
    return cmd


def _run(
    cmd: list[str], *, cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd), check=check, text=True, capture_output=True
    )


def _inspect_container(repo_root: Path, container_name: str) -> dict:
    result = _run(_docker_cmd("inspect", container_name), cwd=repo_root, check=True)
    payload = json.loads(result.stdout)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"Unexpected docker inspect output for {container_name}")
    if not isinstance(payload[0], dict):
        raise RuntimeError(f"Unexpected docker inspect payload for {container_name}")
    return payload[0]


def _bridge_container_ip(inspect_payload: dict) -> str:
    networks = inspect_payload.get("NetworkSettings", {}).get("Networks", {})
    bridge = networks.get("bridge", {})
    ip = bridge.get("IPAddress", "")
    if not isinstance(ip, str) or not ip:
        raise RuntimeError("Container bridge IP not available")
    return ip


def _assert_port_published(
    inspect_payload: dict, *, host_port: int, container_port: int
) -> None:
    ports = inspect_payload.get("NetworkSettings", {}).get("Ports", {})
    key = f"{container_port}/tcp"
    bindings = ports.get(key)
    assert isinstance(bindings, list) and bindings, (
        f"missing published port mapping {key}"
    )
    assert any(
        isinstance(binding, dict) and binding.get("HostPort") == str(host_port)
        for binding in bindings
    ), f"expected host_port={host_port} mapping for {key}, got={bindings}"


def _wait_for_health_from_bridge_peer(
    repo_root: Path,
    *,
    probe_image: str,
    target_ip: str,
    target_port: int,
    timeout_s: float = 40.0,
) -> dict:
    probe_script = """
import sys
import time
import urllib.request

url = sys.argv[1]
deadline = time.time() + float(sys.argv[2])
last_error = ""
while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            if response.status == 200:
                print(response.read().decode("utf-8"))
                raise SystemExit(0)
    except Exception as exc:
        last_error = str(exc)
        time.sleep(0.2)
print(last_error, file=sys.stderr)
raise SystemExit(1)
""".strip()
    url = f"http://{target_ip}:{target_port}/health"
    result = _run(
        _docker_cmd(
            "run",
            "--rm",
            "--network=bridge",
            "--entrypoint",
            "python3",
            probe_image,
            "-c",
            probe_script,
            url,
            str(timeout_s),
        ),
        cwd=repo_root,
        check=True,
    )
    return json.loads(result.stdout)


def _common_env_lines(*, host_port: int, root: str) -> list[str]:
    return [
        "FILE_MCP_AUTH_HEADER_NAME=Authorization",
        "FILE_MCP_AUTH_HEADER_SCHEME=Bearer",
        f"FILE_MCP_ROOT={root}",
        "FILE_MCP_AUDIT_LOG=/workspace/logs/audit.log.jsonl",
        "FILE_MCP_SERVER_LOG=/workspace/logs/server.log",
        "FILE_MCP_SNAPSHOT_DIR=/workspace/logs/snapshots",
        "FILE_MCP_HTTP_TRANSPORT=streamable-http",
        "FILE_MCP_HTTP_HOST=0.0.0.0",
        f"FILE_MCP_HTTP_PORT={host_port}",
        "FILE_MCP_HTTP_BASE_PATH=/",
        "FILE_MCP_HTTP_MCP_PATH=/mcp",
        "FILE_MCP_HTTP_HEALTH_PATH=/health",
        "FILE_MCP_HTTP_EVENTS_PATH=/events",
        "FILE_MCP_HTTP_STATELESS=true",
        "FILE_MCP_SEARCH_MAX_RESULTS=50",
        "FILE_MCP_SEARCH_MAX_FILE_MB=5",
        "FILE_MCP_SEARCH_TIMEOUT_S=15",
        "FILE_MCP_STORAGE_BACKEND=local",
        "FILE_MCP_STORAGE_TLS_INSECURE=false",
        "FILE_MCP_STORAGE_TLS_CA_BUNDLE=",
        "FILE_MCP_STORAGE_TIMEOUT_S=30",
        "FILE_MCP_CONVERSION_TIMEOUT_S=30",
        "FILE_MCP_CONVERSION_MAX_INPUT_MB=20",
        "FILE_MCP_SNAPSHOT_RETENTION_DAYS=30",
        "FILE_MCP_SNAPSHOT_RETENTION_COUNT=-1",
        "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB=-1",
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
        "FILE_MCP_FTP_PORT=21",
        "FILE_MCP_FTP_USERNAME=",
        "FILE_MCP_FTP_PASSWORD=",
        "FILE_MCP_FTP_BASE_DIR=/",
        "FILE_MCP_FTP_USE_TLS=false",
        "FILE_MCP_GDRIVE_USER_EMAIL=",
        "FILE_MCP_GDRIVE_FOLDER_ID=",
        "FILE_MCP_GDRIVE_FOLDER_URL=",
        "FILE_MCP_GDRIVE_CLIENT_ID=",
        "FILE_MCP_GDRIVE_CLIENT_SECRET=",
        "FILE_MCP_GDRIVE_REFRESH_TOKEN=",
        "FILE_MCP_GDRIVE_ACCESS_TOKEN=",
        "FILE_MCP_GDRIVE_AUTH_CODE=",
        "FILE_MCP_GDRIVE_REDIRECT_URI=",
        "FILE_MCP_GDRIVE_TOKEN_URI=",
    ]


def _run_container_detached(repo_root: Path, args: list[str]) -> str:
    result = _run(_docker_cmd(*args), cwd=repo_root)
    return result.stdout.strip()


def _rm_container(repo_root: Path, container_name: str) -> None:
    _run(_docker_cmd("rm", "-f", container_name), cwd=repo_root, check=False)


def _write_runtime_env(tmp_path: Path, *, host_port: int, workspace: Path) -> Path:
    env_path = tmp_path / "docker.env"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "FILE_MCP_API_KEY_PRIMARY=secret",
        *_common_env_lines(host_port=host_port, root="/workspace"),
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def _container_name(suffix: str) -> str:
    return f"file-mcp-docker-test-{suffix}-{int(time.time())}"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        _run(_docker_cmd("info"), cwd=Path.cwd(), check=True)
    except Exception:
        return False
    return True


def _docker_image_exists(repo_root: Path, tag: str) -> bool:
    result = _run(_docker_cmd("image", "inspect", tag), cwd=repo_root, check=False)
    return result.returncode == 0


def _detect_docker_host_endpoint() -> str | None:
    try:
        proc = _run(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            cwd=Path.cwd(),
            check=True,
        )
    except Exception:
        return None
    host = (proc.stdout or "").strip()
    return host or None


@pytest.fixture(scope="session")
def docker_image() -> str:
    if env_get("FILE_MCP_RUN_DOCKER_TESTS", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_DOCKER_TESTS=1 to enable Docker integration tests"
        )
    if not _docker_available():
        pytest.fail("Docker daemon unavailable")

    repo_root = project_root(Path(__file__))
    return require_dev_docker_test_image(repo_root, _docker_cmd())
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_docker_command_builder_supports_remote_host_flag() -> None:
    prev = runtime_env.get("FILE_MCP_DOCKER_HOST")
    runtime_env["FILE_MCP_DOCKER_HOST"] = "tcp://docker-remote:2375"
    try:
        cmd = _docker_cmd("ps")
        assert cmd == ["docker", "-H", "tcp://docker-remote:2375", "ps"]
    finally:
        if prev is None:
            runtime_env.pop("FILE_MCP_DOCKER_HOST", None)
        else:
            runtime_env["FILE_MCP_DOCKER_HOST"] = prev
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_docker_command_builder_defaults_to_local_daemon() -> None:
    prev = runtime_env.pop("FILE_MCP_DOCKER_HOST", None)
    try:
        cmd = _docker_cmd("run", "--rm", "hello-world")
        assert cmd[:2] == ["docker", "run"]
    finally:
        if prev is not None:
            runtime_env["FILE_MCP_DOCKER_HOST"] = prev
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_docker_remote_host_exec_path_if_enabled() -> None:
    if env_get("FILE_MCP_RUN_DOCKER_TESTS", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_DOCKER_TESTS=1 to enable Docker integration tests"
        )
    if not _docker_available():
        pytest.fail("Docker daemon unavailable")
    docker_host = _detect_docker_host_endpoint()
    if not docker_host:
        pytest.fail("Unable to detect a Docker host endpoint from docker context")

    prev = runtime_env.get("FILE_MCP_DOCKER_HOST")
    runtime_env["FILE_MCP_DOCKER_HOST"] = docker_host
    try:
        result = _run(_docker_cmd("ps"), cwd=Path.cwd(), check=True)
        assert result.returncode == 0
    finally:
        if prev is None:
            runtime_env.pop("FILE_MCP_DOCKER_HOST", None)
        else:
            runtime_env["FILE_MCP_DOCKER_HOST"] = prev
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_container_smoke_with_host_network_and_mcp_call(
    docker_image: str, tmp_path: Path
) -> None:
    repo_root = project_root(Path(__file__))
    host_port = _pick_free_port()

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "hello.txt").write_text(
        "hello from docker host network", encoding="utf-8"
    )

    env_path = _write_runtime_env(tmp_path, host_port=host_port, workspace=workspace)
    container_name = _container_name("host")

    _run_container_detached(
        repo_root,
        [
            "run",
            "-d",
            "--name",
            container_name,
            "--network=host",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{env_path}:/workspace/env.base:ro",
            "-e",
            "FILE_MCP_ENV_PATH=/workspace/env.base",
            docker_image,
        ],
    )

    try:
        health = _wait_for_health(f"http://127.0.0.1:{host_port}/health")
        assert health["status"] == "ok"
        assert health["service"] == "file-mcp-server"

        async def _call_read_file(headers: dict[str, str]) -> str:
            transport = StreamableHttpTransport(
                f"http://127.0.0.1:{host_port}/mcp",
                headers=headers,
            )
            async with Client(transport) as client:
                result = await client.call_tool(
                    "read_file", {"path": "/workspace/hello.txt"}
                )
                text_blocks = [
                    item.text for item in result.content if hasattr(item, "text")
                ]
                return "\n".join(text_blocks)

        for auth_headers in (
            {"Authorization": "Bearer secret"},
            {"X-API-Key": "secret"},
        ):
            response_text = asyncio.run(_call_read_file(auth_headers))
            assert "hello from docker host network" in response_text
            with httpx.Client(timeout=10.0) as http_client:
                auth_response = http_client.get(
                    f"http://127.0.0.1:{host_port}/auth/me", headers=auth_headers
                )
                a2a_response = http_client.get(
                    f"http://127.0.0.1:{host_port}/a2a/health", headers=auth_headers
                )
            assert auth_response.status_code == 200
            assert a2a_response.status_code == 200

        with httpx.Client(timeout=10.0) as http_client:
            assert http_client.get(
                f"http://127.0.0.1:{host_port}/auth/me",
                headers={"X-API-Key": "wrong"},
            ).status_code == 401
            assert http_client.get(
                f"http://127.0.0.1:{host_port}/a2a/health",
                headers={"X-API-Key": "wrong"},
            ).status_code == 401
    finally:
        _rm_container(repo_root, container_name)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_container_smoke_with_bridge_network_port_publish(
    docker_image: str, tmp_path: Path
) -> None:
    if env_get("FILE_MCP_RUN_DOCKER_BRIDGE_TESTS", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_DOCKER_BRIDGE_TESTS=1 to enable bridge publish validation"
        )

    repo_root = project_root(Path(__file__))
    host_port = _pick_free_port()
    container_port = 8000

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "bridge.txt").write_text("hello from docker bridge", encoding="utf-8")

    env_path = _write_runtime_env(
        tmp_path, host_port=container_port, workspace=workspace
    )
    container_name = _container_name("bridge")

    _run_container_detached(
        repo_root,
        [
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{host_port}:{container_port}",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{env_path}:/workspace/env.base:ro",
            "-e",
            "FILE_MCP_ENV_PATH=/workspace/env.base",
            docker_image,
        ],
    )

    try:
        inspect_payload = _inspect_container(repo_root, container_name)
        _assert_port_published(
            inspect_payload, host_port=host_port, container_port=container_port
        )
        target_ip = _bridge_container_ip(inspect_payload)
        health = _wait_for_health_from_bridge_peer(
            repo_root,
            probe_image=docker_image,
            target_ip=target_ip,
            target_port=container_port,
            timeout_s=40.0,
        )
        assert health["status"] == "ok"
        assert health["transport"] == "streamable-http"
    finally:
        _rm_container(repo_root, container_name)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_container_multi_env_override_changes_root_and_api_key(
    docker_image: str, tmp_path: Path
) -> None:
    repo_root = project_root(Path(__file__))
    host_port = _pick_free_port()
    workspace = tmp_path / "workspace"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    team_a = workspace / "team_a"
    team_b = workspace / "team_b"
    team_a.mkdir(parents=True, exist_ok=True)
    team_b.mkdir(parents=True, exist_ok=True)
    (team_a / "a.txt").write_text("alpha", encoding="utf-8")
    (team_b / "b.txt").write_text("beta", encoding="utf-8")

    env_base = tmp_path / "env.base"
    env_override = tmp_path / "env.override"
    env_base.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_PRIMARY=base-key",
                *_common_env_lines(host_port=host_port, root="/workspace/team_a"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env_override.write_text(
        "\n".join(
            [
                "FILE_MCP_ROOT=/workspace/team_b",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    container_name = _container_name("multienv")
    _run_container_detached(
        repo_root,
        [
            "run",
            "-d",
            "--name",
            container_name,
            "--network=host",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{env_base}:/workspace/env.base:ro",
            "-v",
            f"{env_override}:/workspace/env.override:ro",
            "-e",
            "FILE_MCP_ENV_PATH=/workspace/env.base,/workspace/env.override",
            "-e",
            "FILE_MCP_API_KEY_PRIMARY=override-key",
            docker_image,
        ],
    )
    try:
        _wait_for_health(f"http://127.0.0.1:{host_port}/health")

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{host_port}/mcp",
                    headers={"Authorization": "Bearer override-key"},
                )
            ) as client:
                allowed = await client.call_tool(
                    "read_file", {"path": "/workspace/team_b/b.txt"}
                )
                assert "beta" in "\n".join(
                    item.text for item in allowed.content if hasattr(item, "text")
                )
                with pytest.raises(Exception):
                    await client.call_tool(
                        "read_file", {"path": "/workspace/team_a/a.txt"}
                    )

            response = httpx.post(
                f"http://127.0.0.1:{host_port}/mcp",
                headers={
                    "Authorization": "Bearer base-key",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": "base-key-rejected",
                    "method": "tools/call",
                    "params": {
                        "name": "read_file",
                        "arguments": {"path": "/workspace/team_b/b.txt"},
                    },
                },
                timeout=5.0,
            )
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "UNAUTHENTICATED"

        asyncio.run(_flow())
        _run(
            _docker_cmd(
                "exec",
                container_name,
                "sh",
                "-lc",
                "chmod -R a+rX /workspace/logs || true",
            ),
            cwd=repo_root,
            check=False,
        )
    finally:
        _rm_container(repo_root, container_name)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_container_multi_folder_scope_controls_and_audit_logs(
    docker_image: str, tmp_path: Path
) -> None:
    repo_root = project_root(Path(__file__))
    host_port = _pick_free_port()
    workspace = tmp_path / "workspace"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    team_a = workspace / "team_a"
    team_b_public = workspace / "team_b" / "public"
    team_b_private = workspace / "team_b" / "private"
    team_a.mkdir(parents=True, exist_ok=True)
    team_b_public.mkdir(parents=True, exist_ok=True)
    team_b_private.mkdir(parents=True, exist_ok=True)
    (team_a / "readme.txt").write_text("team-a-data", encoding="utf-8")
    (team_b_public / "public.txt").write_text("team-b-public", encoding="utf-8")
    (team_b_private / "secret.txt").write_text("team-b-private", encoding="utf-8")

    env_base = tmp_path / "env.base"
    env_override = tmp_path / "env.override"
    config_path = tmp_path / "config.scoped.yaml"
    env_base.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_PRIMARY=base-key",
                *_common_env_lines(host_port=host_port, root="/workspace"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env_override.write_text("FILE_MCP_API_KEY_PRIMARY=override-key\n", encoding="utf-8")
    config_path.write_text(
        """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
      header_name: "${FILE_MCP_AUTH_HEADER_NAME}"
      header_scheme: "${FILE_MCP_AUTH_HEADER_SCHEME}"
    storage:
      backend: "${FILE_MCP_STORAGE_BACKEND}"
      tls:
        insecure_skip_verify: "${FILE_MCP_STORAGE_TLS_INSECURE}"
        ca_bundle_path: "${FILE_MCP_STORAGE_TLS_CA_BUNDLE}"
      s3:
        endpoint: "${FILE_MCP_S3_ENDPOINT}"
        bucket: "${FILE_MCP_S3_BUCKET}"
        region: "${FILE_MCP_S3_REGION}"
        access_key: "${FILE_MCP_S3_ACCESS_KEY}"
        secret_key: "${FILE_MCP_S3_SECRET_KEY}"
        prefix: "${FILE_MCP_S3_PREFIX}"
      webdav:
        base_url: "${FILE_MCP_WEBDAV_BASE_URL}"
        username: "${FILE_MCP_WEBDAV_USERNAME}"
        password: "${FILE_MCP_WEBDAV_PASSWORD}"
      ftp:
        host: "${FILE_MCP_FTP_HOST}"
        port: "${FILE_MCP_FTP_PORT}"
        username: "${FILE_MCP_FTP_USERNAME}"
        password: "${FILE_MCP_FTP_PASSWORD}"
        base_dir: "${FILE_MCP_FTP_BASE_DIR}"
        use_tls: "${FILE_MCP_FTP_USE_TLS}"
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
      allow_globs:
        - "team_a/**"
        - "team_b/public/**"
      deny_globs:
        - "team_b/private/**"
      allowed_exts: []
      read_only_exts: []
    audit:
      log_path: "${FILE_MCP_AUDIT_LOG}"
      include_content_hashes: true
    snapshots:
      enabled: false
      mode: "none"
      dir: "${FILE_MCP_SNAPSHOT_DIR}"
      retention_days: 30
      retention_count: -1
      max_storage_mb: -1
    validation:
      default_mode: "warn"
      per_type: {}
    conversion:
      enabled: false
      backends: []
      max_input_mb: 25
    observability:
      enabled: true
      log_path: "${FILE_MCP_SERVER_LOG}"
      level: "INFO"
    limits:
      search_max_results: 250
      search_max_file_mb: 5
      search_timeout_s: 30
      storage_timeout_s: 30
      conversion_timeout_s: 60
http:
  transport: "${FILE_MCP_HTTP_TRANSPORT}"
  host: "${FILE_MCP_HTTP_HOST}"
  port: "${FILE_MCP_HTTP_PORT}"
  base_path: "${FILE_MCP_HTTP_BASE_PATH}"
  mcp_path: "${FILE_MCP_HTTP_MCP_PATH}"
  health_path: "${FILE_MCP_HTTP_HEALTH_PATH}"
  events_path: "${FILE_MCP_HTTP_EVENTS_PATH}"
  stateless_http: "${FILE_MCP_HTTP_STATELESS}"
""".lstrip(),
        encoding="utf-8",
    )

    container_name = _container_name("multiscope")
    _run_container_detached(
        repo_root,
        [
            "run",
            "-d",
            "--name",
            container_name,
            "--network=host",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{env_base}:/workspace/env.base:ro",
            "-v",
            f"{env_override}:/workspace/env.override:ro",
            "-v",
            f"{config_path}:/workspace/config.scoped.yaml:ro",
            "-e",
            "FILE_MCP_ENV_PATH=/workspace/env.base,/workspace/env.override",
            "-e",
            "FILE_MCP_CONFIG_PATH=/workspace/config.scoped.yaml",
            docker_image,
        ],
    )
    session_id = "session-multi-config"
    try:
        _wait_for_health(f"http://127.0.0.1:{host_port}/health")

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{host_port}/mcp",
                    headers={
                        "Authorization": "Bearer override-key",
                        "X-Session-Id": session_id,
                    },
                )
            ) as client:
                allowed_a = await client.call_tool(
                    "read_file", {"path": "/workspace/team_a/readme.txt"}
                )
                assert "team-a-data" in "\n".join(
                    item.text for item in allowed_a.content if hasattr(item, "text")
                )
                allowed_b = await client.call_tool(
                    "read_file", {"path": "/workspace/team_b/public/public.txt"}
                )
                assert "team-b-public" in "\n".join(
                    item.text for item in allowed_b.content if hasattr(item, "text")
                )
                await client.call_tool(
                    "write_file",
                    {"path": "/workspace/team_a/new.txt", "content": "audit-write-ok"},
                )
                with pytest.raises(Exception):
                    await client.call_tool(
                        "write_file",
                        {
                            "path": "/workspace/team_b/private/blocked.txt",
                            "content": "denied",
                        },
                    )

        asyncio.run(_flow())
        _run(
            _docker_cmd(
                "exec",
                container_name,
                "sh",
                "-lc",
                "chmod -R a+rX /workspace/logs || true",
            ),
            cwd=repo_root,
            check=False,
        )
    finally:
        _rm_container(repo_root, container_name)

    audit_log = workspace / "logs" / "audit.log.jsonl"
    audit_events = _read_jsonl(audit_log)
    assert audit_events, "expected audit events in audit log"
    required_keys = {
        "tool",
        "action",
        "status",
        "outcome",
        "timestamp",
        "profile",
        "session_id",
        "client_ip",
        "duration_ms",
        "params",
        "paths",
        "details",
    }
    assert all(required_keys.issubset(set(event.keys())) for event in audit_events)
    assert all(isinstance(event["tool"], str) for event in audit_events)
    assert all(isinstance(event["action"], str) for event in audit_events)
    assert all(event["status"] in {"ok", "error"} for event in audit_events)
    assert all(event["outcome"] in {"ok", "error"} for event in audit_events)
    assert all(isinstance(event["timestamp"], str) for event in audit_events)
    assert all(
        isinstance(event["profile"], str) and event["profile"] == "default"
        for event in audit_events
    )
    assert all(isinstance(event["params"], dict) for event in audit_events)
    assert all(isinstance(event["paths"], dict) for event in audit_events)
    assert all(isinstance(event["details"], dict) for event in audit_events)
    tool_call_events = [
        event for event in audit_events if event["action"] == "tool_call"
    ]
    assert tool_call_events, "expected tool_call audit events with extended metadata"
    assert all(
        isinstance(event["session_id"], str) and event["session_id"]
        for event in tool_call_events
    )
    assert all(
        isinstance(event["client_ip"], str) and event["client_ip"]
        for event in tool_call_events
    )
    assert all(
        isinstance(event["duration_ms"], (int, float)) for event in tool_call_events
    )
    assert any(event.get("status") == "error" for event in audit_events)

    server_log = workspace / "logs" / "server.log"
    server_log_text = server_log.read_text(encoding="utf-8")
    assert '"event": "tool_call"' in server_log_text
    assert '"event": "tool_result"' in server_log_text
    assert '"tool": "read_file"' in server_log_text
    assert '"profile": "default"' in server_log_text
    assert '"session_id": "session-multi-config"' in server_log_text
    assert '"client_ip": "127.0.0.1"' in server_log_text
    assert '"params"' in server_log_text
    assert '"outcome": "ok"' in server_log_text
    assert '"outcome": "error"' in server_log_text
    assert '"duration_ms"' in server_log_text
