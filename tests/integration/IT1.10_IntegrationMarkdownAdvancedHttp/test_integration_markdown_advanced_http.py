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


def test_markdown_heading_path_slug_and_frontmatter_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "doc.md"
    target.write_text(
        "---\ntitle: Demo\n---\n# Top\ntext\n## Child Section\nold\n",
        encoding="utf-8",
    )

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
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

        async def _flow() -> tuple[dict, dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                by_path = await client.call_tool(
                    "markdown_set_section_file",
                    {
                        "path": str(target),
                        "heading": ["Top", "Child Section"],
                        "new_content": "## Child Section\nnew",
                    },
                )
                by_slug = await client.call_tool(
                    "markdown_set_section_file",
                    {
                        "path": str(target),
                        "heading": "#child-section",
                        "new_content": "## Child Section\nnewer",
                    },
                )
                frontmatter = await client.call_tool(
                    "markdown_set_frontmatter_file",
                    {"path": str(target), "updates": {"release": {"version": "1.2.3"}}},
                )
                return (
                    json.loads(
                        "\n".join(
                            item.text
                            for item in by_path.content
                            if hasattr(item, "text")
                        )
                    ),
                    json.loads(
                        "\n".join(
                            item.text
                            for item in by_slug.content
                            if hasattr(item, "text")
                        )
                    ),
                    json.loads(
                        "\n".join(
                            item.text
                            for item in frontmatter.content
                            if hasattr(item, "text")
                        )
                    ),
                )

        payloads = asyncio.run(_flow())
        for payload in payloads:
            assert payload["ok"] is True

    content = target.read_text(encoding="utf-8")
    assert "newer" in content
    assert "version: 1.2.3" in content
