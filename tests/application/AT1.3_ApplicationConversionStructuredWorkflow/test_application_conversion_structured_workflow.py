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


def test_application_conversion_structured_diff_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    source = root_dir / "input.txt"
    source.write_text("# Section\nold\n", encoding="utf-8")
    converted = root_dir / "converted.md"
    baseline = root_dir / "baseline.md"

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

        async def _flow() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                convert_result = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(source),
                        "target_format": "md",
                        "output_path": str(converted),
                        "backend": "builtin-text-copy",
                    },
                )
                convert_payload = json.loads(
                    "\n".join(item.text for item in convert_result.content if hasattr(item, "text"))
                )
                assert convert_payload["ok"] is True

                copy_result = await client.call_tool(
                    "copy_file",
                    {"src": str(converted), "dst": str(baseline), "overwrite": True},
                )
                copy_payload = json.loads("\n".join(item.text for item in copy_result.content if hasattr(item, "text")))
                assert copy_payload["ok"] is True

                edit_result = await client.call_tool(
                    "markdown_set_section_file",
                    {"path": str(converted), "heading": "Section", "new_content": "new"},
                )
                edit_payload = json.loads("\n".join(item.text for item in edit_result.content if hasattr(item, "text")))
                assert edit_payload["ok"] is True

                diff_result = await client.call_tool(
                    "diff_files",
                    {"path_a": str(baseline), "path_b": str(converted)},
                )
                return json.loads("\n".join(item.text for item in diff_result.content if hasattr(item, "text")))

        diff_payload = asyncio.run(_flow())
        assert diff_payload["ok"] is True
        assert "-old" in diff_payload["diff"]
        assert "+new" in diff_payload["diff"]

    assert converted.exists()
    assert "new" in converted.read_text(encoding="utf-8")
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    tools = [json.loads(line).get("tool") for line in lines]
    assert "markdown_set_section_file" in tools

