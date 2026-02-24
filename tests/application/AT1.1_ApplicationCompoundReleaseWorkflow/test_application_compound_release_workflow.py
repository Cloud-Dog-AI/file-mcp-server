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


def test_application_compound_release_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    notes_src = root_dir / "release_notes.txt"
    notes_src.write_text("# Release\nTODO item\n", encoding="utf-8")
    notes_md = root_dir / "release_notes.md"
    baseline_md = root_dir / "release_notes.baseline.md"
    state_json = root_dir / "state.json"
    state_json.write_text('{"release":{"status":"TODO","version":"1.0.0"}}', encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=20,
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

        async def _flow() -> tuple[dict, dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                before = await client.call_tool(
                    "search_content",
                    {"query": "TODO", "glob": "state.json"},
                )
                before_payload = json.loads("\n".join(item.text for item in before.content if hasattr(item, "text")))

                convert_result = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(notes_src),
                        "target_format": "md",
                        "output_path": str(notes_md),
                        "backend": "builtin-text-copy",
                    },
                )
                convert_payload = json.loads(
                    "\n".join(item.text for item in convert_result.content if hasattr(item, "text"))
                )
                assert convert_payload["ok"] is True

                copy_result = await client.call_tool(
                    "copy_file",
                    {"src": str(notes_md), "dst": str(baseline_md), "overwrite": True},
                )
                copy_payload = json.loads("\n".join(item.text for item in copy_result.content if hasattr(item, "text")))
                assert copy_payload["ok"] is True

                md_edit = await client.call_tool(
                    "markdown_set_section_file",
                    {"path": str(notes_md), "heading": "Release", "new_content": "DONE item"},
                )
                md_edit_payload = json.loads("\n".join(item.text for item in md_edit.content if hasattr(item, "text")))
                assert md_edit_payload["ok"] is True

                json_edit = await client.call_tool(
                    "json_set_file",
                    {"path": str(state_json), "json_path": "/release/status", "value": "DONE"},
                )
                json_edit_payload = json.loads(
                    "\n".join(item.text for item in json_edit.content if hasattr(item, "text"))
                )
                assert json_edit_payload["ok"] is True

                diff_result = await client.call_tool(
                    "diff_files",
                    {"path_a": str(baseline_md), "path_b": str(notes_md)},
                )
                diff_payload = json.loads("\n".join(item.text for item in diff_result.content if hasattr(item, "text")))

                after = await client.call_tool(
                    "search_content",
                    {"query": "TODO", "glob": "state.json"},
                )
                after_payload = json.loads("\n".join(item.text for item in after.content if hasattr(item, "text")))
                return before_payload, diff_payload, after_payload

        before_payload, diff_payload, after_payload = asyncio.run(_flow())
        assert before_payload["matches"]
        assert diff_payload["ok"] is True
        assert "-TODO item" in diff_payload["diff"]
        assert "+DONE item" in diff_payload["diff"]
        assert after_payload["matches"] == []

    assert "DONE item" in notes_md.read_text(encoding="utf-8")
    state = json.loads(state_json.read_text(encoding="utf-8"))
    assert state["release"]["status"] == "DONE"
    events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    tools = {evt.get("tool") for evt in events}
    assert "markdown_set_section_file" in tools
    assert "json_set_file" in tools
