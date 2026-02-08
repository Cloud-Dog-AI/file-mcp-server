from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

from tests.http_integration_helpers import pick_free_port, running_server, wait_for_health, write_server_config


def test_read_file_partial_line_and_byte_ranges(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "sample.txt"
    target.write_text("line1\nline2\nline3\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(tmp_path, port=port, root_dir=root_dir)
    repo_root = Path(__file__).resolve().parents[1]
    with running_server(
        repo_root, defaults_path=defaults_path, config_path=config_path, env_path=env_path, pidfile=pidfile
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _calls() -> tuple[str, str]:
            async with Client(
                StreamableHttpTransport(f"http://127.0.0.1:{port}/mcp", headers={"Authorization": "Bearer secret"})
            ) as client:
                by_line = await client.call_tool(
                    "read_file",
                    {"path": str(target), "start_line": 2, "end_line": 3},
                )
                by_byte = await client.call_tool(
                    "read_file",
                    {"path": str(target), "start_byte": 0, "end_byte": 5},
                )
                line_payload = "\n".join(item.text for item in by_line.content if hasattr(item, "text"))
                byte_payload = "\n".join(item.text for item in by_byte.content if hasattr(item, "text"))
                return line_payload, byte_payload

        line_payload, byte_payload = asyncio.run(_calls())
        assert line_payload == "line2\nline3\n"
        assert byte_payload == "line1"


def test_read_file_rejects_mixed_line_and_byte_ranges(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "sample.txt"
    target.write_text("line1\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(tmp_path, port=port, root_dir=root_dir)
    repo_root = Path(__file__).resolve().parents[1]
    with running_server(
        repo_root, defaults_path=defaults_path, config_path=config_path, env_path=env_path, pidfile=pidfile
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _invalid_call() -> None:
            async with Client(
                StreamableHttpTransport(f"http://127.0.0.1:{port}/mcp", headers={"Authorization": "Bearer secret"})
            ) as client:
                await client.call_tool(
                    "read_file",
                    {
                        "path": str(target),
                        "start_line": 1,
                        "end_line": 1,
                        "start_byte": 0,
                        "end_byte": 1,
                    },
                )

        with pytest.raises(ToolError, match="Cannot combine line and byte ranges"):
            asyncio.run(_invalid_call())
