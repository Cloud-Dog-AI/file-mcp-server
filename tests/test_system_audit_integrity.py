from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_audit_log_integrity_append_only(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
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

        async def _mutate() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                src = root_dir / "a.txt"
                dst = root_dir / "b.txt"
                await client.call_tool("write_file", {"path": str(src), "content": "hello"})
                await client.call_tool("copy_file", {"src": str(src), "dst": str(dst)})
                await client.call_tool("delete_file", {"path": str(dst)})

        asyncio.run(_mutate())

    assert audit_log.exists()
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 3
    events = [json.loads(line) for line in lines]
    for event in events:
        assert "timestamp" in event
        assert "tool" in event
        assert "action" in event
        assert "status" in event
