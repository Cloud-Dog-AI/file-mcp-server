from __future__ import annotations

import asyncio
import json
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


def test_sed_transaction_contract_validation_and_noop(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "doc.json"
    txt_target = root_dir / "doc.txt"
    json_target.write_text('{"a":1}', encoding="utf-8")
    txt_target.write_text("alpha\nbeta\n", encoding="utf-8")
    json_before = json_target.read_text(encoding="utf-8")
    txt_before = txt_target.read_text(encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        validation_default_mode="strict",
        validation_per_type={"json": "strict"},
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

        async def _invalid_json_transaction() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(json_target),
                        "operations": [
                            {"op": "replace_regex", "pattern": r"\{", "repl": ""},
                        ],
                    },
                )

        async def _noop_transaction() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(txt_target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "not-present", "repl": "X"},
                        ],
                    },
                )
                return json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))

        with pytest.raises(Exception):
            asyncio.run(_invalid_json_transaction())
        noop_payload = asyncio.run(_noop_transaction())
        assert noop_payload["ok"] is True

    assert json_target.read_text(encoding="utf-8") == json_before
    assert txt_target.read_text(encoding="utf-8") == txt_before

    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    events = [json.loads(line) for line in lines if json.loads(line).get("tool") == "sed_edit_file"]
    assert events
    assert any(evt["status"] == "error" for evt in events)
    assert any(evt["status"] == "ok" for evt in events)


def test_sed_transaction_ordering_and_policy_variants(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "ordered.json"
    md_target = root_dir / "ordered.md"
    json_target.write_text('{"a":1}', encoding="utf-8")
    md_target.write_text("# Title\n## Section\nBody\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        validation_default_mode="strict",
        validation_per_type={"json": "strict", "markdown": "warn"},
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

        async def _json_ordered() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(json_target),
                        "operations": [
                            {"op": "replace_regex", "pattern": '"a":1', "repl": '"a":2'},
                            {"op": "replace_regex", "pattern": '"a":2', "repl": '"a":3'},
                        ],
                    },
                )
                return json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))

        async def _markdown_warn() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(md_target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "## Section", "repl": "#### Section"},
                        ],
                    },
                )
                return json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))

        json_payload = asyncio.run(_json_ordered())
        md_payload = asyncio.run(_markdown_warn())
        assert json_payload["ok"] is True
        assert md_payload["ok"] is True
        assert md_payload["warnings"]

    json_doc = json.loads(json_target.read_text(encoding="utf-8"))
    assert json_doc["a"] == 3
    assert "#### Section" in md_target.read_text(encoding="utf-8")
