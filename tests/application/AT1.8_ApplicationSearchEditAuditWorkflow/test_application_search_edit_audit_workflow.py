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
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_application_search_edit_audit_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "tasks.txt"
    target.write_text("TODO one\nTODO two\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=10,
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

        async def _flow() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                search_before = await client.call_tool(
                    "search_content", {"query": "TODO"}
                )
                search_before_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in search_before.content
                        if hasattr(item, "text")
                    )
                )
                edit_result = await client.call_tool(
                    "sed_edit_file",
                    {
                        "path": str(target),
                        "operations": [
                            {"op": "replace_regex", "pattern": "TODO", "repl": "DONE"},
                        ],
                    },
                )
                edit_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in edit_result.content
                        if hasattr(item, "text")
                    )
                )
                assert edit_payload["ok"] is True
                search_after = await client.call_tool(
                    "search_content", {"query": "TODO"}
                )
                search_after_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in search_after.content
                        if hasattr(item, "text")
                    )
                )
                return search_before_payload, search_after_payload

        before_payload, after_payload = asyncio.run(_flow())
        assert len(before_payload["matches"]) == 2
        assert after_payload["matches"] == []

    text = target.read_text(encoding="utf-8")
    assert "DONE one" in text
    assert "TODO" not in text
    lines = [
        line
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(json.loads(line).get("tool") == "sed_edit_file" for line in lines)
