from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tests.path_helpers import project_root

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_security_boundary_enforcement_with_audit(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside"
    outside.mkdir(parents=True, exist_ok=True)
    bad_target = outside / "bad.txt"

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _denied_write() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool("write_file", {"path": str(bad_target), "content": "x"})

        with pytest.raises(Exception):
            asyncio.run(_denied_write())

    assert audit_log.exists()
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    event = json.loads(lines[-1])
    assert event["tool"] == "write_file"
    assert event["status"] == "error"
