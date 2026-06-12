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

"""Remote backend MCP tool matrix integration tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Exercises a broad MCP file-tool matrix across remote backends.
Requirements: FR1.26, FR1.27, FR1.28, FR1.29, FR1.30, FR1.31
Tasks: T22, T23
Architecture: 9. Storage Backend Architecture
Tests: IT1.16
"""

from __future__ import annotations

from tests.env_runtime import env_get

import asyncio
from pathlib import Path
from typing import Mapping
import uuid

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
)
from tests.remote_env_helpers import (
    file_mcp_env_values,
    merged_remote_env,
    write_env_file,
)


_RUN_GOOGLE_LIVE = env_get("FILE_MCP_RUN_GOOGLE_LIVE_TESTS", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_BACKEND_MATRIX = ["webdav", "ftp", "s3"] + (
    ["google_drive"] if _RUN_GOOGLE_LIVE else []
)


def _is_unresolved_placeholder(value: str) -> bool:
    candidate = value.strip()
    return bool(candidate) and candidate.startswith("${") and candidate.endswith("}")


def _strict_remote_mode(env: Mapping[str, str]) -> bool:
    value = env.get("FILE_MCP_STRICT_REMOTE_TESTS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _require(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {key}")
    if _is_unresolved_placeholder(value):
        raise RuntimeError(f"Unresolved placeholder env var: {key}")
    return value


def _get(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, "").strip()
    return value if value else default


def _configured(env: Mapping[str, str], key: str) -> bool:
    value = _get(env, key, "")
    return bool(value) and not _is_unresolved_placeholder(value)


def _backend_ready(backend: str, env: Mapping[str, str]) -> bool:
    if backend == "webdav":
        return bool(
            _configured(env, "FILE_MCP_WEBDAV_BASE_URL")
            and _configured(env, "FILE_MCP_WEBDAV_USERNAME")
            and _configured(env, "FILE_MCP_WEBDAV_PASSWORD")
        )
    if backend == "ftp":
        return bool(
            _configured(env, "FILE_MCP_FTP_HOST")
            and _configured(env, "FILE_MCP_FTP_USERNAME")
            and _configured(env, "FILE_MCP_FTP_PASSWORD")
        )
    if backend == "s3":
        return bool(
            _configured(env, "FILE_MCP_S3_ENDPOINT")
            and _configured(env, "FILE_MCP_S3_BUCKET")
            and _configured(env, "FILE_MCP_S3_ACCESS_KEY")
            and _configured(env, "FILE_MCP_S3_SECRET_KEY")
        )
    if backend == "google_drive":
        return bool(
            _configured(env, "FILE_MCP_GDRIVE_CLIENT_ID")
            and _configured(env, "FILE_MCP_GDRIVE_CLIENT_SECRET")
            and (
                _configured(env, "FILE_MCP_GDRIVE_FOLDER_ID")
                or _configured(env, "FILE_MCP_GDRIVE_FOLDER_URL")
            )
            and (
                _configured(env, "FILE_MCP_GDRIVE_REFRESH_TOKEN")
                or _configured(env, "FILE_MCP_GDRIVE_ACCESS_TOKEN")
            )
        )
    return False
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


@pytest.mark.parametrize("backend", _BACKEND_MATRIX)
def test_remote_backend_tool_matrix(backend: str, tmp_path: Path) -> None:
    repo_root = Path.cwd()
    env_ctx = merged_remote_env(repo_root, include_google=(backend == "google_drive"))
    strict = _strict_remote_mode(env_ctx)
    if not strict and env_get("FILE_MCP_RUN_REMOTE_MATRIX_TESTS", "0") != "1":
        pytest.skip(
            "Set FILE_MCP_RUN_REMOTE_MATRIX_TESTS=1 to run remote backend matrix tests"
        )
    if not _backend_ready(backend, env_ctx):
        if strict:
            raise AssertionError(
                f"Backend {backend} credentials unresolved/missing for matrix test"
            )
        pytest.skip(f"Backend {backend} credentials not configured for matrix test")

    port = pick_free_port()
    run_id = uuid.uuid4().hex[:10]
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_path = tmp_path / f"matrix-{backend}.env"
    runtime_env = file_mcp_env_values(env_ctx)

    extra_env: dict[str, str] = {
        "FILE_MCP_HTTP_PORT": str(port),
        "FILE_MCP_API_KEY_PRIMARY": _require(env_ctx, "FILE_MCP_API_KEY_PRIMARY"),
        "FILE_MCP_AUTH_HEADER_NAME": _get(
            env_ctx, "FILE_MCP_AUTH_HEADER_NAME", "Authorization"
        ),
        "FILE_MCP_AUTH_HEADER_SCHEME": _get(
            env_ctx, "FILE_MCP_AUTH_HEADER_SCHEME", "Bearer"
        ),
        "FILE_MCP_STORAGE_BACKEND": backend,
        "CLOUD_DOG__PROFILES__DEFAULT__STORAGE__BACKEND": backend,
        "FILE_MCP_ROOT": "/",
        "FILE_MCP_AUDIT_LOG": f"./working/remote-storage/audit.matrix.{backend}.log.jsonl",
        "FILE_MCP_SERVER_LOG": f"./working/remote-storage/server.matrix.{backend}.log",
        "FILE_MCP_SNAPSHOT_DIR": f"./working/remote-storage/snapshots.matrix.{backend}",
        "FILE_MCP_SNAPSHOT_RETENTION_DAYS": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_DAYS", "30"
        ),
        "FILE_MCP_SNAPSHOT_RETENTION_COUNT": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_COUNT", "-1"
        ),
        "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB": _get(
            env_ctx, "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB", "-1"
        ),
        "FILE_MCP_STORAGE_TIMEOUT_S": _get(env_ctx, "FILE_MCP_STORAGE_TIMEOUT_S", "30"),
        "FILE_MCP_SEARCH_TIMEOUT_S": _get(env_ctx, "FILE_MCP_SEARCH_TIMEOUT_S", "30"),
    }
    if backend == "webdav":
        extra_env.update(
            {
                "FILE_MCP_WEBDAV_BASE_URL": _require(
                    env_ctx, "FILE_MCP_WEBDAV_BASE_URL"
                ),
                "FILE_MCP_WEBDAV_USERNAME": _require(
                    env_ctx, "FILE_MCP_WEBDAV_USERNAME"
                ),
                "FILE_MCP_WEBDAV_PASSWORD": _require(
                    env_ctx, "FILE_MCP_WEBDAV_PASSWORD"
                ),
            }
        )
    elif backend == "ftp":
        extra_env.update(
            {
                "FILE_MCP_FTP_HOST": _require(env_ctx, "FILE_MCP_FTP_HOST"),
                "FILE_MCP_FTP_PORT": _get(env_ctx, "FILE_MCP_FTP_PORT", "21"),
                "FILE_MCP_FTP_USERNAME": _require(env_ctx, "FILE_MCP_FTP_USERNAME"),
                "FILE_MCP_FTP_PASSWORD": _require(env_ctx, "FILE_MCP_FTP_PASSWORD"),
                "FILE_MCP_FTP_BASE_DIR": _get(env_ctx, "FILE_MCP_FTP_BASE_DIR", "/"),
                "FILE_MCP_FTP_USE_TLS": _get(env_ctx, "FILE_MCP_FTP_USE_TLS", "false"),
            }
        )
    elif backend == "s3":
        extra_env.update(
            {
                "FILE_MCP_S3_ENDPOINT": _require(env_ctx, "FILE_MCP_S3_ENDPOINT"),
                "FILE_MCP_S3_BUCKET": _require(env_ctx, "FILE_MCP_S3_BUCKET"),
                "FILE_MCP_S3_REGION": _get(env_ctx, "FILE_MCP_S3_REGION", "us-east-1"),
                "FILE_MCP_S3_ACCESS_KEY": _require(env_ctx, "FILE_MCP_S3_ACCESS_KEY"),
                "FILE_MCP_S3_SECRET_KEY": _require(env_ctx, "FILE_MCP_S3_SECRET_KEY"),
                "FILE_MCP_S3_PREFIX": f"file-mcp-matrix/{run_id}",
            }
        )
    elif backend == "google_drive":
        extra_env.update(
            {
                "FILE_MCP_GDRIVE_USER_EMAIL": _get(
                    env_ctx, "FILE_MCP_GDRIVE_USER_EMAIL", ""
                ),
                "FILE_MCP_GDRIVE_FOLDER_ID": _get(
                    env_ctx, "FILE_MCP_GDRIVE_FOLDER_ID", ""
                ),
                "FILE_MCP_GDRIVE_FOLDER_URL": _get(
                    env_ctx, "FILE_MCP_GDRIVE_FOLDER_URL", ""
                ),
                "FILE_MCP_GDRIVE_CLIENT_ID": _require(
                    env_ctx, "FILE_MCP_GDRIVE_CLIENT_ID"
                ),
                "FILE_MCP_GDRIVE_CLIENT_SECRET": _require(
                    env_ctx, "FILE_MCP_GDRIVE_CLIENT_SECRET"
                ),
                "FILE_MCP_GDRIVE_REFRESH_TOKEN": _get(
                    env_ctx, "FILE_MCP_GDRIVE_REFRESH_TOKEN", ""
                ),
                "FILE_MCP_GDRIVE_ACCESS_TOKEN": _get(
                    env_ctx, "FILE_MCP_GDRIVE_ACCESS_TOKEN", ""
                ),
                "FILE_MCP_GDRIVE_REDIRECT_URI": _get(
                    env_ctx, "FILE_MCP_GDRIVE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob"
                ),
                "FILE_MCP_GDRIVE_TOKEN_URI": _get(
                    env_ctx,
                    "FILE_MCP_GDRIVE_TOKEN_URI",
                    "https://oauth2.googleapis.com/token",
                ),
            }
        )
    Path("./working/remote-storage").mkdir(parents=True, exist_ok=True)
    runtime_env.update(extra_env)
    write_env_file(env_path, runtime_env)
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=tmp_path / f"matrix-{backend}.pid",
        extra_env=extra_env,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=20.0)

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={
                        "Authorization": f"Bearer {_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}"
                    },
                )
            ) as client:

                async def _call_with_retry(tool: str, arguments: dict) -> object:
                    attempts = 3 if backend == "webdav" else 1
                    for idx in range(attempts):
                        try:
                            return await client.call_tool(tool, arguments)
                        except Exception as exc:
                            locked = "423" in str(exc) or "locked" in str(exc).lower()
                            if backend == "webdav" and locked and idx + 1 < attempts:
                                await asyncio.sleep(0.4)
                                continue
                            raise

                base = f"/matrix-{backend}-{run_id}"
                file_a = f"{base}/a.txt"
                file_b = f"{base}/b.txt"
                moved = f"{base}/moved.txt"
                renamed = f"{base}/renamed.txt"
                json_path = f"{base}/data.json"
                yaml_path = f"{base}/data.yaml"
                md_path = f"{base}/doc.md"
                xml_path = f"{base}/data.xml"
                html_path = f"{base}/data.html"

                if backend != "s3":
                    await _call_with_retry(
                        "create_dir", {"path": base, "parents": True, "exist_ok": True}
                    )
                else:
                    with pytest.raises(Exception) as excinfo:
                        await client.call_tool(
                            "create_dir",
                            {"path": base, "parents": True, "exist_ok": True},
                        )
                    assert "Not supported for backend" in str(excinfo.value)

                await _call_with_retry(
                    "write_file",
                    {"path": file_a, "content": f"hello {backend} {run_id}\n"},
                )
                await _call_with_retry(
                    "copy_file", {"src": file_a, "dst": file_b, "overwrite": True}
                )
                await _call_with_retry(
                    "move_path", {"src": file_b, "dst": moved, "overwrite": True}
                )
                await _call_with_retry(
                    "rename_path", {"src": moved, "dst": renamed, "overwrite": True}
                )

                await _call_with_retry(
                    "write_file", {"path": json_path, "content": '{"x":1}\n'}
                )
                await _call_with_retry(
                    "json_set_file",
                    {
                        "path": json_path,
                        "json_path": "/y",
                        "value": 2,
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "json_copy_file",
                    {
                        "path": json_path,
                        "from_path": "/y",
                        "to_path": "/z",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "json_move_file",
                    {
                        "path": json_path,
                        "from_path": "/z",
                        "to_path": "/moved",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "json_merge_file",
                    {
                        "path": json_path,
                        "json_path": "/",
                        "value": {"k": "v"},
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "json_get_file", {"path": json_path, "json_path": "/moved"}
                )

                await _call_with_retry(
                    "write_file", {"path": yaml_path, "content": "root:\n  a: 1\n"}
                )
                await _call_with_retry(
                    "yaml_set_file",
                    {
                        "path": yaml_path,
                        "yaml_path": "/root/b",
                        "value": 2,
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "yaml_copy_file",
                    {
                        "path": yaml_path,
                        "from_path": "/root/b",
                        "to_path": "/root/c",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "yaml_move_file",
                    {
                        "path": yaml_path,
                        "from_path": "/root/c",
                        "to_path": "/root/d",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "yaml_merge_file",
                    {
                        "path": yaml_path,
                        "yaml_path": "/root",
                        "value": {"e": 5},
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "yaml_delete_file",
                    {"path": yaml_path, "yaml_path": "/root/a", "dry_run": False},
                )
                await _call_with_retry(
                    "yaml_get_file", {"path": yaml_path, "yaml_path": "/root/d"}
                )

                await _call_with_retry(
                    "write_file", {"path": md_path, "content": "# Title\n\nBody\n"}
                )
                await _call_with_retry(
                    "markdown_set_section_file",
                    {
                        "path": md_path,
                        "heading": "Title",
                        "new_content": "Updated body",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "markdown_set_frontmatter_file",
                    {"path": md_path, "updates": {"owner": "matrix"}, "dry_run": False},
                )
                await _call_with_retry(
                    "write_file",
                    {"path": xml_path, "content": "<root><item>1</item></root>\n"},
                )
                await _call_with_retry(
                    "xml_set_file",
                    {
                        "path": xml_path,
                        "xpath": "/root/item",
                        "value": "2",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "write_file",
                    {
                        "path": html_path,
                        "content": "<html><body><p id='m'>x</p></body></html>\n",
                    },
                )
                await _call_with_retry(
                    "html_set_file",
                    {
                        "path": html_path,
                        "selector": "#m",
                        "value": "y",
                        "dry_run": False,
                    },
                )
                await _call_with_retry(
                    "sed_edit_file",
                    {
                        "path": file_a,
                        "operations": [
                            {"op": "replace_regex", "pattern": "hello", "repl": "hi"}
                        ],
                    },
                )

                b64 = await client.call_tool("b64_encode_file", {"path": file_a})
                data = b64.data.get("data") if hasattr(b64, "data") else None
                assert isinstance(data, str) and data
                await _call_with_retry(
                    "b64_decode_to_file",
                    {"path": f"{base}/decoded.txt", "data": data, "overwrite": True},
                )

                await client.call_tool("list_dir", {"path": base, "recursive": True})
                await client.call_tool(
                    "search_paths", {"query": "data", "max_depth": 3, "timeout_s": 10}
                )
                await client.call_tool(
                    "search_content",
                    {
                        "query": run_id,
                        "max_depth": 4,
                        "timeout_s": 10,
                        "max_results": 20,
                    },
                )
                await client.call_tool("validate_file", {"path": json_path})
                await client.call_tool(
                    "diff_files", {"path_a": file_a, "path_b": renamed}
                )
                status = await client.call_tool("backend_status", {})
                status_payload = status.data if hasattr(status, "data") else {}
                assert status_payload.get("active_backend") == backend

                with pytest.raises(Exception) as excinfo:
                    await client.call_tool(
                        "chmod_path", {"path": file_a, "mode": "0644"}
                    )
                assert "Not supported for backend" in str(excinfo.value)

                await _call_with_retry(
                    "delete_file", {"path": file_a, "missing_ok": True}
                )

        asyncio.run(_flow())

    audit_path = Path(f"./working/remote-storage/audit.matrix.{backend}.log.jsonl")
    assert audit_path.exists()
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "write_file" in audit_text
    assert "json_set_file" in audit_text
    assert "yaml_set_file" in audit_text
