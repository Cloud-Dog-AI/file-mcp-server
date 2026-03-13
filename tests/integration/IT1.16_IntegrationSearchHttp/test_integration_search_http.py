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


def test_search_http_honors_scope_deny_and_limits(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    public_dir = root_dir / "public"
    private_dir = root_dir / "private"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    (public_dir / "a.txt").write_text("needle one\n", encoding="utf-8")
    (public_dir / "b.txt").write_text("needle two\n", encoding="utf-8")
    (public_dir / "c.txt").write_text("needle three\n", encoding="utf-8")
    (private_dir / "secret.txt").write_text("needle private\n", encoding="utf-8")
    (public_dir / "huge.txt").write_text(
        "needle\n" + ("x" * (2 * 1024 * 1024)), encoding="utf-8"
    )

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        deny_globs=["private/**"],
        search_max_results=2,
        search_max_file_mb=1,
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

        async def _calls() -> tuple[dict, dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                path_result = await client.call_tool(
                    "search_paths", {"query": "secret"}
                )
                regex_result = await client.call_tool(
                    "search_paths", {"query": r"public/.+\\.txt$", "regex": True}
                )
                content_result = await client.call_tool(
                    "search_content", {"query": "needle"}
                )
                path_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in path_result.content
                        if hasattr(item, "text")
                    )
                )
                regex_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in regex_result.content
                        if hasattr(item, "text")
                    )
                )
                content_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in content_result.content
                        if hasattr(item, "text")
                    )
                )
                return path_payload, regex_payload, content_payload

        path_payload, regex_payload, content_payload = asyncio.run(_calls())

        assert path_payload["matches"] == []
        assert all("private" not in match for match in regex_payload["matches"])
        assert all(
            "private" not in match["path"] for match in content_payload["matches"]
        )
        assert all(
            "huge.txt" not in match["path"] for match in content_payload["matches"]
        )
        assert len(content_payload["matches"]) == 2
