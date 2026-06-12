# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tests.path_helpers import project_root

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
import pytest
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_dry_run_mutations_do_not_change_files_and_are_audited(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.txt"
    target.write_text("before\n", encoding="utf-8")
    src = root_dir / "src.txt"
    src.write_text("copy-me\n", encoding="utf-8")
    dst = root_dir / "dst.txt"

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path, port=port, root_dir=root_dir
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

        async def _calls() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                calls = [
                    (
                        "write_file",
                        {"path": str(target), "content": "after\n", "dry_run": True},
                    ),
                    ("copy_file", {"src": str(src), "dst": str(dst), "dry_run": True}),
                    ("move_file", {"src": str(src), "dst": str(dst), "dry_run": True}),
                    ("delete_file", {"path": str(target), "dry_run": True}),
                    (
                        "sed_edit_file",
                        {
                            "path": str(target),
                            "operations": [
                                {
                                    "op": "replace_regex",
                                    "pattern": "before",
                                    "repl": "after",
                                }
                            ],
                            "dry_run": True,
                        },
                    ),
                ]
                for name, args in calls:
                    result = await client.call_tool(name, args)
                    payload = json.loads(
                        "\n".join(
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        )
                    )
                    assert payload["ok"] is True
                    assert payload["dry_run"] is True

        asyncio.run(_calls())

    assert target.read_text(encoding="utf-8") == "before\n"
    assert src.exists()
    assert not dst.exists()
    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dry_tools = {
        evt["tool"] for evt in events if evt.get("details", {}).get("dry_run") is True
    }
    for expected in {
        "write_file",
        "copy_file",
        "move_file",
        "delete_file",
        "sed_edit_file",
    }:
        assert expected in dry_tools
