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


def test_error_contract_for_expected_operational_failures(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    too_large = root_dir / "large.md"
    too_large.write_text("x" * (2 * 1024 * 1024), encoding="utf-8")
    unsupported = root_dir / "blob.bin"
    unsupported.write_bytes(b"\x00\x01")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        conversion_max_input_mb=1,
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

        async def _calls() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                large_result = await client.call_tool(
                    "convert_file",
                    {"path": str(too_large), "target_format": "txt"},
                )
                unsupported_result = await client.call_tool(
                    "convert_file",
                    {"path": str(unsupported), "target_format": "txt"},
                )
                large_payload = json.loads(
                    "\n".join(item.text for item in large_result.content if hasattr(item, "text"))
                )
                unsupported_payload = json.loads(
                    "\n".join(item.text for item in unsupported_result.content if hasattr(item, "text"))
                )
                return large_payload, unsupported_payload

        large_payload, unsupported_payload = asyncio.run(_calls())
        for payload in (large_payload, unsupported_payload):
            assert "ok" in payload
            assert "warnings" in payload
            assert payload["ok"] is False
            assert isinstance(payload["warnings"], list)
