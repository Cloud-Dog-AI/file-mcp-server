from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tests.path_helpers import project_root

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_limits_search_and_conversion_size(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / "a.txt").write_text("needle\n", encoding="utf-8")
    (root_dir / "b.txt").write_text("needle\n", encoding="utf-8")
    large = root_dir / "large.md"
    large.write_text("x" * (2 * 1024 * 1024), encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=1,
        conversion_max_input_mb=1,
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

        async def _run() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                search_result = await client.call_tool(
                    "search_content",
                    {"query": "needle"},
                )
                convert_result = await client.call_tool(
                    "convert_file",
                    {"path": str(large), "target_format": "txt"},
                )
                search_payload = json.loads("\n".join(item.text for item in search_result.content if hasattr(item, "text")))
                convert_payload = json.loads("\n".join(item.text for item in convert_result.content if hasattr(item, "text")))
                return search_payload, convert_payload

        search_payload, convert_payload = asyncio.run(_run())
        assert len(search_payload["matches"]) == 1
        assert convert_payload["ok"] is False
        assert any("size limit" in warning.lower() for warning in convert_payload["warnings"])
