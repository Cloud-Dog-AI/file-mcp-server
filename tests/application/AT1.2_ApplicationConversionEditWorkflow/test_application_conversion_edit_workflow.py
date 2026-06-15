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
@pytest.mark.req("FR-027")


def test_conversion_plus_markdown_edit_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    source = root_dir / "input.txt"
    source.write_text("# Section\nold\n", encoding="utf-8")
    converted = root_dir / "converted.md"

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

        async def _flow() -> None:
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
                    },
                )
                convert_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in convert_result.content
                        if hasattr(item, "text")
                    )
                )
                assert convert_payload["ok"] is True
                assert Path(convert_payload["output_path"]) == converted

                edit_result = await client.call_tool(
                    "markdown_set_section_file",
                    {
                        "path": str(converted),
                        "heading": "Section",
                        "new_content": "new",
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

        asyncio.run(_flow())

    assert converted.exists()
    assert "new" in converted.read_text(encoding="utf-8")
    lines = [
        line
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(
        json.loads(line).get("tool") == "markdown_set_section_file" for line in lines
    )
