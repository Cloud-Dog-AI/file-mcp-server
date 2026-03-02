from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Mapping

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _merged_env() -> dict[str, str]:
    merged: dict[str, str] = {}
    merged.update(_parse_env_file(Path("private/env-preprod-filemcp")))
    merged.update(dict(os.environ))
    return merged


def _require(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {key}")
    return value


def _text(result: object) -> str:
    content = getattr(result, "content", [])
    return "".join(getattr(item, "text", "") for item in content)


async def _call_tool(
    *,
    base_url: str,
    profile: str,
    api_key: str,
    tool: str,
    arguments: dict,
) -> object:
    async with Client(
        StreamableHttpTransport(
            f"{base_url}/mcp",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-File-MCP-Profile": profile,
                "Accept": "application/json",
            },
        )
    ) as client:
        return await client.call_tool(tool, arguments)


def test_application_preprod_profile_chain_flow_live() -> None:
    if os.getenv("FILE_MCP_RUN_PREPROD_AT", "0") != "1":
        pytest.fail("Set FILE_MCP_RUN_PREPROD_AT=1 to run preprod profile-chain AT test")

    env = _merged_env()
    base_url = _require(env, "FILE_MCP_PREPROD_URL")
    profile_local = env.get("FILE_MCP_PREPROD_PROFILE_LOCAL", "default").strip() or "default"
    profile_s3 = env.get("FILE_MCP_PREPROD_PROFILE_S3", "s3").strip() or "s3"
    profile_webdav = env.get("FILE_MCP_PREPROD_PROFILE_WEBDAV", "webdav").strip() or "webdav"
    profile_ftp = env.get("FILE_MCP_PREPROD_PROFILE_FTP", "ftp").strip() or "ftp"

    key_local = _require(env, "FILE_MCP_PREPROD_KEY_LOCAL")
    key_s3 = _require(env, "FILE_MCP_PREPROD_KEY_S3")
    key_webdav = _require(env, "FILE_MCP_PREPROD_KEY_WEBDAV")
    key_ftp = _require(env, "FILE_MCP_PREPROD_KEY_FTP")

    run_id = uuid.uuid4().hex[:10]
    base_dir = env.get("FILE_MCP_PREPROD_AT_BASE_DIR", f"/workspace/at-profile-chain-{run_id}").strip()
    filename = env.get("FILE_MCP_PREPROD_AT_FILENAME", "chain.txt").strip() or "chain.txt"

    local_path = f"{base_dir}/local/{filename}"
    s3_path = f"{base_dir}/s3/{filename}"
    webdav_path = f"{base_dir}/webdav/{filename}"
    ftp_path = f"{base_dir}/ftp/{filename}"

    async def _flow() -> None:
        # Local: add -> update -> download
        await _call_tool(
            base_url=base_url,
            profile=profile_local,
            api_key=key_local,
            tool="create_dir",
            arguments={"path": f"{base_dir}/local", "parents": True, "exist_ok": True},
        )
        seed = f"flow:{run_id}:v1"
        await _call_tool(
            base_url=base_url,
            profile=profile_local,
            api_key=key_local,
            tool="write_file",
            arguments={"path": local_path, "content": seed + "\n"},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_local,
            api_key=key_local,
            tool="sed_edit_file",
            arguments={
                "path": local_path,
                "operations": [{"op": "replace_regex", "pattern": "v1", "repl": "v2-local"}],
            },
        )
        local_read = await _call_tool(
            base_url=base_url,
            profile=profile_local,
            api_key=key_local,
            tool="read_file",
            arguments={"path": local_path},
        )
        local_text = _text(local_read)
        assert "v2-local" in local_text

        # S3: upload from local content -> update -> download
        await _call_tool(
            base_url=base_url,
            profile=profile_s3,
            api_key=key_s3,
            tool="write_file",
            arguments={"path": s3_path, "content": local_text},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_s3,
            api_key=key_s3,
            tool="sed_edit_file",
            arguments={
                "path": s3_path,
                "operations": [{"op": "replace_regex", "pattern": "v2-local", "repl": "v3-s3"}],
            },
        )
        s3_read = await _call_tool(
            base_url=base_url,
            profile=profile_s3,
            api_key=key_s3,
            tool="read_file",
            arguments={"path": s3_path},
        )
        s3_text = _text(s3_read)
        assert "v3-s3" in s3_text

        # WebDAV: upload from S3 content -> update -> download
        await _call_tool(
            base_url=base_url,
            profile=profile_webdav,
            api_key=key_webdav,
            tool="create_dir",
            arguments={"path": f"{base_dir}/webdav", "parents": True, "exist_ok": True},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_webdav,
            api_key=key_webdav,
            tool="write_file",
            arguments={"path": webdav_path, "content": s3_text},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_webdav,
            api_key=key_webdav,
            tool="sed_edit_file",
            arguments={
                "path": webdav_path,
                "operations": [{"op": "replace_regex", "pattern": "v3-s3", "repl": "v4-webdav"}],
            },
        )
        webdav_read = await _call_tool(
            base_url=base_url,
            profile=profile_webdav,
            api_key=key_webdav,
            tool="read_file",
            arguments={"path": webdav_path},
        )
        webdav_text = _text(webdav_read)
        assert "v4-webdav" in webdav_text

        # FTP: upload from WebDAV content -> update -> download
        await _call_tool(
            base_url=base_url,
            profile=profile_ftp,
            api_key=key_ftp,
            tool="create_dir",
            arguments={"path": f"{base_dir}/ftp", "parents": True, "exist_ok": True},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_ftp,
            api_key=key_ftp,
            tool="write_file",
            arguments={"path": ftp_path, "content": webdav_text},
        )
        await _call_tool(
            base_url=base_url,
            profile=profile_ftp,
            api_key=key_ftp,
            tool="sed_edit_file",
            arguments={
                "path": ftp_path,
                "operations": [{"op": "replace_regex", "pattern": "v4-webdav", "repl": "v5-ftp"}],
            },
        )
        ftp_read = await _call_tool(
            base_url=base_url,
            profile=profile_ftp,
            api_key=key_ftp,
            tool="read_file",
            arguments={"path": ftp_path},
        )
        ftp_text = _text(ftp_read)
        assert "v5-ftp" in ftp_text

    asyncio.run(_flow())
