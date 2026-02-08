from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_scoped_file_operations_over_http(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    repo_root = Path(__file__).resolve().parents[1]
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                src = root_dir / "a.txt"
                copy_dst = root_dir / "b.txt"
                move_dst = root_dir / "c.txt"
                outside = outside_dir / "bad.txt"

                await client.call_tool("write_file", {"path": str(src), "content": "abc"})
                read_result = await client.call_tool("read_file", {"path": str(src)})
                assert any(getattr(item, "text", "") == "abc" for item in read_result.content)

                await client.call_tool("copy_file", {"src": str(src), "dst": str(copy_dst)})
                await client.call_tool("move_file", {"src": str(copy_dst), "dst": str(move_dst)})
                await client.call_tool("delete_file", {"path": str(move_dst)})

                with pytest.raises(Exception):
                    await client.call_tool("write_file", {"path": str(outside), "content": "x"})

        asyncio.run(_flow())
