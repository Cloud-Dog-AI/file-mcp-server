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


def test_sedlike_transaction_atomicity_over_http(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.txt"
    original = "alpha\nbeta\ngamma\n"
    target.write_text(original, encoding="utf-8")

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

        async def _invalid_transaction() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "beta", "repl": "BETA"},
                            {"op": "insert_before_line", "line_no": 99, "content": "bad"},
                        ],
                    },
                )

        with pytest.raises(Exception):
            asyncio.run(_invalid_transaction())

        assert target.read_text(encoding="utf-8") == original

        async def _valid_transaction() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "beta", "repl": "BETA"},
                            {"op": "delete_matching_lines", "pattern": "gamma"},
                        ],
                    },
                )
                payload = json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))
                assert payload["ok"] is True

        asyncio.run(_valid_transaction())

    text = target.read_text(encoding="utf-8")
    assert "BETA" in text
    assert "gamma" not in text
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(json.loads(line).get("tool") == "sed_edit_file" for line in lines)


def test_sedlike_transaction_validation_failure_rolls_back(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.md"
    original = "# Title\n## Section\nBody\n"
    target.write_text(original, encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        validation_default_mode="strict",
        validation_per_type={"markdown": "strict"},
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

        async def _invalid_markdown_transaction() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "## Section", "repl": "#### Section"},
                            {"op": "insert_after_line", "line_no": 3, "content": "tail"},
                        ],
                    },
                )

        with pytest.raises(Exception):
            asyncio.run(_invalid_markdown_transaction())

    assert target.read_text(encoding="utf-8") == original
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    last_event = json.loads(lines[-1])
    assert last_event["tool"] == "sed_edit_file"
    assert last_event["status"] == "error"
