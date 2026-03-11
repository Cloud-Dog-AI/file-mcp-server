from __future__ import annotations

import asyncio
import json
import stat
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


def _decode_result(result):
    structured = getattr(result, "structuredContent", None)
    if structured not in (None, {}):
        return structured
    text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
    return json.loads(text)


def test_filesystem_path_tools_cover_files_dirs_and_utf8(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

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
        health = wait_for_health(f"http://127.0.0.1:{port}/health")
        assert health["status"] == "ok"
        assert health["application"]["name"] == "file-mcp-server"
        assert health["runtime"]["env_file"] == str(env_path.resolve())

        source_dir = root_dir / "naive-测试"
        source_file = source_dir / "résumé-🙂.txt"
        renamed_file = source_dir / "renamed-ß.txt"
        moved_dir = root_dir / "moved-δοκιμή"

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                payload = _decode_result(
                    await client.call_tool("create_dir", {"path": str(source_dir)})
                )
                assert payload["ok"] is True

                payload = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(source_file), "content": "utf8 payload"},
                    )
                )
                assert payload["ok"] is True

                payload = _decode_result(
                    await client.call_tool(
                        "chmod_path",
                        {"path": str(source_file), "mode": "640"},
                    )
                )
                assert payload["ok"] is True

                payload = _decode_result(
                    await client.call_tool(
                        "rename_path",
                        {"src": str(source_file), "dst": str(renamed_file)},
                    )
                )
                assert payload["ok"] is True

                payload = _decode_result(
                    await client.call_tool(
                        "move_path",
                        {"src": str(source_dir), "dst": str(moved_dir)},
                    )
                )
                assert payload["ok"] is True

        asyncio.run(_flow())

    final_file = moved_dir / "renamed-ß.txt"
    assert final_file.exists()
    assert final_file.read_text(encoding="utf-8") == "utf8 payload"
    assert stat.S_IMODE(final_file.stat().st_mode) == 0o640

    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    tool_names = {event.get("tool") for event in events}
    for expected in {
        "create_dir",
        "chmod_path",
        "rename_path",
        "move_path",
        "write_file",
    }:
        assert expected in tool_names
