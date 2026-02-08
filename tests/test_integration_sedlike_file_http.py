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


def test_sedlike_file_edit_flow_over_http(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

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

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                ops = [
                    {"op": "replace_regex", "pattern": "beta", "repl": "BETA"},
                    {"op": "insert_before_line", "line_no": 1, "content": "start"},
                    {"op": "delete_matching_lines", "pattern": "gamma"},
                    {"op": "replace_line_range", "start": 2, "end": 2, "replacement": ["middle"]},
                ]
                for op_args in ops:
                    payload_args = {"path": str(target), **op_args}
                    result = await client.call_tool("sed_edit_file", payload_args)
                    payload = json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))
                    assert payload["ok"] is True

        asyncio.run(_flow())

    text = target.read_text(encoding="utf-8")
    assert "start" in text
    assert "middle" in text
    assert "gamma" not in text
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(json.loads(line).get("tool") == "sed_edit_file" for line in lines)
