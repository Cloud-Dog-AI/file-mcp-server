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


def test_structured_file_edits_xml_html_markdown(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    xml_file = root_dir / "doc.xml"
    html_file = root_dir / "doc.html"
    md_file = root_dir / "doc.md"

    xml_file.write_text("<root><item>old</item></root>", encoding="utf-8")
    html_file.write_text("<html><body><p>old</p></body></html>", encoding="utf-8")
    md_file.write_text("# Section\nold\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
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

        async def _edits() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                for name, args in [
                    (
                        "xml_set_file",
                        {"path": str(xml_file), "xpath": "/root/item", "value": "new"},
                    ),
                    (
                        "html_set_file",
                        {"path": str(html_file), "selector": "p", "value": "new"},
                    ),
                    (
                        "markdown_set_section_file",
                        {
                            "path": str(md_file),
                            "heading": "Section",
                            "new_content": "new",
                        },
                    ),
                ]:
                    result = await client.call_tool(name, args)
                    payload = json.loads(
                        "\n".join(
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        )
                    )
                    assert payload["ok"] is True

        asyncio.run(_edits())

    assert "<item>new</item>" in xml_file.read_text(encoding="utf-8")
    assert "<p>new</p>" in html_file.read_text(encoding="utf-8")
    assert "new" in md_file.read_text(encoding="utf-8")
