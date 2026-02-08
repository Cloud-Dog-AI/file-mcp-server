from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_snapshot_retention_prunes_old_snapshot_dirs(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.json"
    target.write_text('{"a":1}', encoding="utf-8")

    snapshots_dir = tmp_path / "snapshots"
    stale = snapshots_dir / "20000101T000000Z" / "stale.txt"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        snapshot_retention_days=0,
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
                await client.call_tool(
                    "json_set_file",
                    {"path": str(target), "json_path": "/a", "value": 2},
                )

        asyncio.run(_mutate())

    assert not (snapshots_dir / "20000101T000000Z").exists()
    assert list(snapshots_dir.rglob("doc.json")), "expected fresh snapshot after mutation"
