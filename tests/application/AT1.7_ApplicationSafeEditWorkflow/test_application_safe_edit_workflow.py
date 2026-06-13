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
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
import pytest
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_end_to_end_safe_edit_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.json"
    target.write_text('{"title":"Old","body":"x"}', encoding="utf-8")

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
                read_before = await client.call_tool("read_file", {"path": str(target)})
                before_text = "\n".join(
                    item.text for item in read_before.content if hasattr(item, "text")
                )

                edited_preview = json.dumps({"title": "New", "body": "x"}, indent=2)
                diff_result = await client.call_tool(
                    "diff_text",
                    {"before": before_text, "after": edited_preview, "context": 3},
                )
                diff_text = "\n".join(
                    item.text for item in diff_result.content if hasattr(item, "text")
                )

                mutate = await client.call_tool(
                    "json_set_file",
                    {"path": str(target), "json_path": "/title", "value": "New"},
                )
                mutate_payload = json.loads(
                    "\n".join(
                        item.text for item in mutate.content if hasattr(item, "text")
                    )
                )
                return {"diff": diff_text, "mutate": mutate_payload}

        payload = asyncio.run(_flow())
        assert "Old" in payload["diff"] and "New" in payload["diff"]
        assert payload["mutate"]["ok"] is True

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["title"] == "New"

    lines = [
        line
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(json.loads(line).get("tool") == "json_set_file" for line in lines)
