from __future__ import annotations

import uuid
from pathlib import Path
from typing import Mapping

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import pick_free_port, running_server, wait_for_health
from tests.remote_env_helpers import file_mcp_env_values, merged_remote_env, write_env_file


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        pytest.skip(f"Missing required env var for live remote backend test: {name}")
    if value.startswith("${") and value.endswith("}"):
        pytest.skip(
            f"Unresolved placeholder for live remote backend test env var: {name}"
        )
    return value


def _get(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name, "").strip()
    return value if value else default


def _base_env(backend: str, env_ctx: Mapping[str, str]) -> dict[str, str]:
    env = {
        "FILE_MCP_STORAGE_BACKEND": backend,
        "FILE_MCP_ROOT": "/",
        # Keep logs/snapshots local; path is intentionally inside repo working/.
        "FILE_MCP_AUDIT_LOG": "./working/remote-storage/audit.log.jsonl",
        "FILE_MCP_SERVER_LOG": "./working/remote-storage/server.log",
        "FILE_MCP_SNAPSHOT_DIR": "./working/remote-storage/snapshots",
    }
    env.update(
        {
            # Snapshot controls are required by schema.
            "FILE_MCP_SNAPSHOT_RETENTION_DAYS": _get(env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_DAYS", "30"),
            "FILE_MCP_SNAPSHOT_RETENTION_COUNT": _get(env_ctx, "FILE_MCP_SNAPSHOT_RETENTION_COUNT", "-1"),
            "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB": _get(env_ctx, "FILE_MCP_SNAPSHOT_MAX_STORAGE_MB", "-1"),
        }
    )
    return env


@pytest.mark.parametrize("backend", ["webdav", "ftp", "s3"])
def test_remote_storage_backend_end_to_end(tmp_path: Path, backend: str) -> None:
    """
    Real end-to-end verification against remote endpoints.

    This test must be run in a network-capable runner with credentials provided
    via env file(s) in the config precedence chain.
    """

    port = pick_free_port()
    run_id = uuid.uuid4().hex[:12]

    # Use the repo defaults/config to avoid duplicating YAML and to preserve precedence rules.
    repo_root = Path.cwd()
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_ctx = merged_remote_env(repo_root)
    env_path = tmp_path / "remote-storage.env"
    write_env_file(env_path, file_mcp_env_values(env_ctx))

    # Fail fast if core auth is not available (used by client transport).
    _require(env_ctx, "FILE_MCP_API_KEY_PRIMARY")

    extra_env = _base_env(backend, env_ctx)
    # Ensure the subprocess server binds to the selected port.
    extra_env["FILE_MCP_HTTP_PORT"] = str(port)
    extra_env["FILE_MCP_API_KEY_PRIMARY"] = _require(env_ctx, "FILE_MCP_API_KEY_PRIMARY")
    extra_env["FILE_MCP_AUTH_HEADER_NAME"] = _get(env_ctx, "FILE_MCP_AUTH_HEADER_NAME", "Authorization")
    extra_env["FILE_MCP_AUTH_HEADER_SCHEME"] = _get(env_ctx, "FILE_MCP_AUTH_HEADER_SCHEME", "Bearer")

    if backend == "webdav":
        extra_env.update(
            {
                "FILE_MCP_WEBDAV_BASE_URL": _require(env_ctx, "FILE_MCP_WEBDAV_BASE_URL"),
                "FILE_MCP_WEBDAV_USERNAME": _require(env_ctx, "FILE_MCP_WEBDAV_USERNAME"),
                "FILE_MCP_WEBDAV_PASSWORD": _require(env_ctx, "FILE_MCP_WEBDAV_PASSWORD"),
            }
        )
    elif backend == "ftp":
        extra_env.update(
            {
                "FILE_MCP_FTP_HOST": _require(env_ctx, "FILE_MCP_FTP_HOST"),
                "FILE_MCP_FTP_USERNAME": _require(env_ctx, "FILE_MCP_FTP_USERNAME"),
                "FILE_MCP_FTP_PASSWORD": _require(env_ctx, "FILE_MCP_FTP_PASSWORD"),
                "FILE_MCP_FTP_PORT": _get(env_ctx, "FILE_MCP_FTP_PORT", "21"),
                "FILE_MCP_FTP_BASE_DIR": _get(env_ctx, "FILE_MCP_FTP_BASE_DIR", "/"),
                "FILE_MCP_FTP_USE_TLS": _get(env_ctx, "FILE_MCP_FTP_USE_TLS", "false"),
            }
        )
    elif backend == "s3":
        extra_env.update(
            {
                "FILE_MCP_S3_ENDPOINT": _require(env_ctx, "FILE_MCP_S3_ENDPOINT"),
                "FILE_MCP_S3_BUCKET": _require(env_ctx, "FILE_MCP_S3_BUCKET"),
                "FILE_MCP_S3_ACCESS_KEY": _require(env_ctx, "FILE_MCP_S3_ACCESS_KEY"),
                "FILE_MCP_S3_SECRET_KEY": _require(env_ctx, "FILE_MCP_S3_SECRET_KEY"),
                "FILE_MCP_S3_REGION": _get(env_ctx, "FILE_MCP_S3_REGION", "us-east-1"),
                "FILE_MCP_S3_PREFIX": f"file-mcp-it/{run_id}",
            }
        )

    # Ensure local artefact dirs exist.
    Path("./working/remote-storage").mkdir(parents=True, exist_ok=True)

    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=tmp_path / "remote-storage.pid",
        extra_env=extra_env,
    ) as process:
        # Ensure the server is actually listening before client connect.
        # (The server is started as a subprocess and may take a moment to bind.)
        wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=15.0)

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": f"Bearer {_require(env_ctx, 'FILE_MCP_API_KEY_PRIMARY')}"},
                )
            ) as client:
                base_dir = f"/it-{run_id}"
                path_txt = f"{base_dir}/hello.txt"
                path_txt2 = f"{base_dir}/hello2.txt"

                if backend != "s3":
                    await client.call_tool("create_dir", {"path": base_dir, "parents": True, "exist_ok": True})

                # write/read
                await client.call_tool("write_file", {"path": path_txt, "content": f"hello {backend} {run_id}\n"})
                read = await client.call_tool("read_file", {"path": path_txt})
                text = "".join(getattr(item, "text", "") for item in read.content)
                assert f"hello {backend}" in text

                # copy/move/rename
                await client.call_tool("copy_file", {"src": path_txt, "dst": path_txt2, "overwrite": True})
                await client.call_tool(
                    "move_path",
                    {"src": path_txt2, "dst": f"{base_dir}/moved.txt", "overwrite": True},
                )
                await client.call_tool(
                    "rename_path",
                    {"src": f"{base_dir}/moved.txt", "dst": f"{base_dir}/renamed.txt", "overwrite": True},
                )

                # diff_files
                await client.call_tool("write_file", {"path": f"{base_dir}/a.txt", "content": "A\n"})
                await client.call_tool("write_file", {"path": f"{base_dir}/b.txt", "content": "B\n"})
                diff = await client.call_tool(
                    "diff_files", {"path_a": f"{base_dir}/a.txt", "path_b": f"{base_dir}/b.txt"}
                )
                assert any(getattr(item, "text", "") for item in diff.content)

                # validate_file (json)
                await client.call_tool("write_file", {"path": f"{base_dir}/x.json", "content": '{"a": 1}\n'})
                valid = await client.call_tool("validate_file", {"path": f"{base_dir}/x.json"})
                payload = valid.data if hasattr(valid, "data") else {}
                assert payload.get("valid") is True

                # structured edit (json_set_file)
                await client.call_tool(
                    "json_set_file",
                    {"path": f"{base_dir}/x.json", "json_path": "/b", "value": 2, "dry_run": False},
                )
                after = await client.call_tool("read_file", {"path": f"{base_dir}/x.json"})
                after_text = "".join(getattr(item, "text", "") for item in after.content)
                assert '"b"' in after_text

                # sed-like edit
                await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": path_txt,
                        "operations": [{"op": "replace_regex", "pattern": "hello", "repl": "hi"}],
                    },
                )
                edited = await client.call_tool("read_file", {"path": path_txt})
                edited_text = "".join(getattr(item, "text", "") for item in edited.content)
                assert "hi" in edited_text

                # base64 roundtrip
                b64 = await client.call_tool("b64_encode_file", {"path": path_txt})
                data = b64.data.get("data") if hasattr(b64, "data") else None
                assert isinstance(data, str) and data
                await client.call_tool(
                    "b64_decode_to_file",
                    {"path": f"{base_dir}/b64.txt", "data": data, "overwrite": True},
                )
                b64read = await client.call_tool("read_file", {"path": f"{base_dir}/b64.txt"})
                b64_text = "".join(getattr(item, "text", "") for item in b64read.content)
                assert "hi" in b64_text

                # search params: depth/timeout/max_results
                await client.call_tool("search_paths", {"query": "hello", "max_depth": 2, "timeout_s": 10})
                await client.call_tool(
                    "search_content",
                    {"query": run_id, "max_depth": 3, "timeout_s": 10, "max_results": 5},
                )

                # not supported check: chmod_path must fail for remote backends
                with pytest.raises(Exception) as excinfo:
                    await client.call_tool("chmod_path", {"path": path_txt, "mode": "0644"})
                assert "Not supported for backend" in str(excinfo.value)

                # cleanup
                await client.call_tool("delete_file", {"path": path_txt, "missing_ok": True})

        import asyncio

        asyncio.run(_flow())

    # Audit log should exist and contain evidence of mutation operations.
    audit_path = Path("./working/remote-storage/audit.log.jsonl")
    assert audit_path.exists()
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "write_file" in audit_text
    assert "json_set_file" in audit_text
