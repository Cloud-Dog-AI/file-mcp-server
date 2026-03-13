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

"""Docker container remote storage backend tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Validate that the containerized server works against real WebDAV/FTP/S3 endpoints.
"""

from __future__ import annotations

from tests.env_runtime import env_get

import asyncio
import json
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from tests.path_helpers import project_root
from typing import Mapping
from urllib.request import urlopen

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.remote_env_helpers import merged_remote_env


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(url: str, timeout_s: float = 30.0) -> dict:
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


def _rm_container(repo_root: Path, container_name: str) -> None:
    _run(_docker_cmd("rm", "-f", container_name), cwd=repo_root, check=False)


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


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _container_name(suffix: str) -> str:
    return f"file-mcp-docker-remote-{suffix}-{int(time.time())}"


@pytest.fixture(scope="session")
def docker_image() -> str:
    if env_get("FILE_MCP_RUN_DOCKER_TESTS", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_DOCKER_TESTS=1 to enable Docker integration tests"
        )
    if env_get("FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS", "0") != "1":
        pytest.fail(
            "Set FILE_MCP_RUN_DOCKER_REMOTE_STORAGE_TESTS=1 to enable remote storage Docker tests"
        )
    if not _docker_available():
        pytest.fail("Docker daemon unavailable")

    repo_root = project_root(Path(__file__))
    requested = env_get("FILE_MCP_DOCKER_TEST_IMAGE", "").strip()
    if requested:
        if not _docker_image_exists(repo_root, requested):
            raise RuntimeError(f"Requested docker test image not found: {requested}")
        return requested

    prebuilt_tag = "cloud-dog/file-mcp-server:w5f"
    if _docker_image_exists(repo_root, prebuilt_tag):
        return prebuilt_tag

    tag = "cloud-dog/file-mcp-server:test"
    _run(_docker_cmd("build", "--network=host", "-t", tag, "."), cwd=repo_root)
    return tag


@pytest.mark.parametrize("backend", ["webdav", "ftp", "s3"])
def test_container_remote_storage_backend_over_host_network(
    docker_image: str, tmp_path: Path, backend: str
) -> None:
    repo_root = project_root(Path(__file__))
    env_ctx = merged_remote_env(repo_root)

    # Validate required creds without hardcoding.
    _require(env_ctx, "FILE_MCP_API_KEY_PRIMARY")
    if backend == "webdav":
        _require(env_ctx, "FILE_MCP_WEBDAV_BASE_URL")
        _require(env_ctx, "FILE_MCP_WEBDAV_USERNAME")
        _require(env_ctx, "FILE_MCP_WEBDAV_PASSWORD")
    if backend == "ftp":
        _require(env_ctx, "FILE_MCP_FTP_HOST")
        _require(env_ctx, "FILE_MCP_FTP_USERNAME")
        _require(env_ctx, "FILE_MCP_FTP_PASSWORD")
    if backend == "s3":
        _require(env_ctx, "FILE_MCP_S3_ENDPOINT")
        _require(env_ctx, "FILE_MCP_S3_BUCKET")
        _require(env_ctx, "FILE_MCP_S3_ACCESS_KEY")
        _require(env_ctx, "FILE_MCP_S3_SECRET_KEY")

    host_port = _pick_free_port()
    run_id = uuid.uuid4().hex[:12]

    workspace = tmp_path / "workspace"
    (workspace / "logs").mkdir(parents=True, exist_ok=True)

    # Provide a CA bundle file for the container entrypoint (trust-store install is best-effort).
    host_ca_bundle = Path("/etc/ssl/certs/ca-certificates.crt")
    if not host_ca_bundle.exists():
        raise RuntimeError(
            "Host CA bundle not found at /etc/ssl/certs/ca-certificates.crt"
        )

    env_path = tmp_path / f"env.{backend}"
    lines = [
        f"FILE_MCP_API_KEY_PRIMARY={_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}",
        "FILE_MCP_AUTH_HEADER_NAME=Authorization",
        "FILE_MCP_AUTH_HEADER_SCHEME=Bearer",
        "FILE_MCP_ROOT=/",
        f"FILE_MCP_AUDIT_LOG=/workspace/logs/audit.{backend}.log.jsonl",
        f"FILE_MCP_SERVER_LOG=/workspace/logs/server.{backend}.log",
        f"FILE_MCP_SNAPSHOT_DIR=/workspace/logs/snapshots.{backend}",
        "FILE_MCP_HTTP_TRANSPORT=streamable-http",
        "FILE_MCP_HTTP_HOST=0.0.0.0",
        f"FILE_MCP_HTTP_PORT={host_port}",
        "FILE_MCP_HTTP_BASE_PATH=/",
        "FILE_MCP_HTTP_MCP_PATH=/mcp",
        "FILE_MCP_HTTP_HEALTH_PATH=/health",
        "FILE_MCP_HTTP_EVENTS_PATH=/events",
        "FILE_MCP_HTTP_STATELESS=true",
        "FILE_MCP_SEARCH_MAX_RESULTS=25",
        "FILE_MCP_SEARCH_MAX_FILE_MB=5",
        "FILE_MCP_SEARCH_TIMEOUT_S=30",
        "FILE_MCP_STORAGE_TIMEOUT_S=30",
        "FILE_MCP_CONVERSION_TIMEOUT_S=60",
        "FILE_MCP_CONVERSION_MAX_INPUT_MB=25",
        "FILE_MCP_SNAPSHOT_RETENTION_DAYS=30",
        "FILE_MCP_SNAPSHOT_RETENTION_COUNT=-1",
        "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB=-1",
        f"FILE_MCP_STORAGE_BACKEND={backend}",
        "FILE_MCP_STORAGE_TLS_INSECURE=false",
        "FILE_MCP_STORAGE_TLS_CA_BUNDLE=/app/certs/ca.crt",
    ]
    if backend == "webdav":
        lines.extend(
            [
                f"FILE_MCP_WEBDAV_BASE_URL={_require(env_ctx, 'FILE_MCP_WEBDAV_BASE_URL')}",
                f"FILE_MCP_WEBDAV_USERNAME={_require(env_ctx, 'FILE_MCP_WEBDAV_USERNAME')}",
                f"FILE_MCP_WEBDAV_PASSWORD={_require(env_ctx, 'FILE_MCP_WEBDAV_PASSWORD')}",
            ]
        )
    if backend == "ftp":
        lines.extend(
            [
                f"FILE_MCP_FTP_HOST={_require(env_ctx, 'FILE_MCP_FTP_HOST')}",
                f"FILE_MCP_FTP_PORT={env_ctx.get('FILE_MCP_FTP_PORT', '21')}",
                f"FILE_MCP_FTP_USERNAME={_require(env_ctx, 'FILE_MCP_FTP_USERNAME')}",
                f"FILE_MCP_FTP_PASSWORD={_require(env_ctx, 'FILE_MCP_FTP_PASSWORD')}",
                f"FILE_MCP_FTP_BASE_DIR={env_ctx.get('FILE_MCP_FTP_BASE_DIR', '/')}",
                f"FILE_MCP_FTP_USE_TLS={env_ctx.get('FILE_MCP_FTP_USE_TLS', 'false')}",
            ]
        )
    if backend == "s3":
        lines.extend(
            [
                f"FILE_MCP_S3_ENDPOINT={_require(env_ctx, 'FILE_MCP_S3_ENDPOINT')}",
                f"FILE_MCP_S3_BUCKET={_require(env_ctx, 'FILE_MCP_S3_BUCKET')}",
                f"FILE_MCP_S3_REGION={env_ctx.get('FILE_MCP_S3_REGION', 'us-east-1')}",
                f"FILE_MCP_S3_ACCESS_KEY={_require(env_ctx, 'FILE_MCP_S3_ACCESS_KEY')}",
                f"FILE_MCP_S3_SECRET_KEY={_require(env_ctx, 'FILE_MCP_S3_SECRET_KEY')}",
                f"FILE_MCP_S3_PREFIX=file-mcp-docker-it/{run_id}",
            ]
        )

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    container_name = _container_name(backend)
    _run(
        _docker_cmd(
            "run",
            "-d",
            "--name",
            container_name,
            "--network=host",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{env_path}:/workspace/env.base:ro",
            "-v",
            f"{host_ca_bundle}:/app/certs/ca.crt:ro",
            "-e",
            "FILE_MCP_ENV_PATH=/workspace/env.base",
            "-e",
            "FILE_MCP_TLS_CA_BUNDLE=/app/certs/ca.crt",
            docker_image,
        ),
        cwd=repo_root,
        check=True,
    )

    try:
        health = _wait_for_health(f"http://127.0.0.1:{host_port}/health")
        assert health["status"] == "ok"
        assert health["service"] == "file-mcp-server"

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{host_port}/mcp",
                    headers={
                        "Authorization": f"Bearer {_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}"
                    },
                )
            ) as client:
                base_dir = f"/it-{backend}-{run_id}"
                path_txt = f"{base_dir}/hello.txt"
                path_txt2 = f"{base_dir}/hello2.txt"

                if backend != "s3":
                    await client.call_tool(
                        "create_dir",
                        {"path": base_dir, "parents": True, "exist_ok": True},
                    )

                await client.call_tool(
                    "write_file",
                    {"path": path_txt, "content": f"hello {backend} {run_id}\n"},
                )
                read = await client.call_tool("read_file", {"path": path_txt})
                text = "".join(getattr(item, "text", "") for item in read.content)
                assert f"hello {backend}" in text

                await client.call_tool(
                    "copy_file", {"src": path_txt, "dst": path_txt2, "overwrite": True}
                )
                await client.call_tool(
                    "move_path",
                    {
                        "src": path_txt2,
                        "dst": f"{base_dir}/moved.txt",
                        "overwrite": True,
                    },
                )
                await client.call_tool(
                    "rename_path",
                    {
                        "src": f"{base_dir}/moved.txt",
                        "dst": f"{base_dir}/renamed.txt",
                        "overwrite": True,
                    },
                )

                await client.call_tool(
                    "write_file",
                    {"path": f"{base_dir}/x.json", "content": '{"a": 1}\n'},
                )
                valid = await client.call_tool(
                    "validate_file", {"path": f"{base_dir}/x.json"}
                )
                payload = valid.data if hasattr(valid, "data") else {}
                assert payload.get("valid") is True

                await client.call_tool(
                    "json_set_file",
                    {
                        "path": f"{base_dir}/x.json",
                        "json_path": "/b",
                        "value": 2,
                        "dry_run": False,
                    },
                )

                await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": path_txt,
                        "operations": [
                            {"op": "replace_regex", "pattern": "hello", "repl": "hi"}
                        ],
                    },
                )
                edited = await client.call_tool("read_file", {"path": path_txt})
                edited_text = "".join(
                    getattr(item, "text", "") for item in edited.content
                )
                assert "hi" in edited_text

                b64 = await client.call_tool("b64_encode_file", {"path": path_txt})
                data = b64.data.get("data") if hasattr(b64, "data") else None
                assert isinstance(data, str) and data
                await client.call_tool(
                    "b64_decode_to_file",
                    {"path": f"{base_dir}/b64.txt", "data": data, "overwrite": True},
                )

                search_timeout = 30 if backend == "webdav" else 10
                await client.call_tool(
                    "search_paths",
                    {"query": run_id, "max_depth": 3, "timeout_s": search_timeout},
                )
                await client.call_tool(
                    "search_content",
                    {
                        "query": run_id,
                        "max_depth": 3,
                        "timeout_s": search_timeout,
                        "max_results": 5,
                    },
                )

                with pytest.raises(Exception) as excinfo:
                    await client.call_tool(
                        "chmod_path", {"path": path_txt, "mode": "0644"}
                    )
                assert "Not supported for backend" in str(excinfo.value)

                await client.call_tool(
                    "delete_file", {"path": path_txt, "missing_ok": True}
                )

        asyncio.run(_flow())

        audit_path = workspace / "logs" / f"audit.{backend}.log.jsonl"
        assert audit_path.exists()
        audit_text = audit_path.read_text(encoding="utf-8")
        assert "write_file" in audit_text
        assert "json_set_file" in audit_text
    finally:
        _rm_container(repo_root, container_name)
