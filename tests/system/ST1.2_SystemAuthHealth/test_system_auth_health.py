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
from pathlib import Path
from urllib.request import urlopen
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
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.req("FR-028")


def test_auth_enforcement_and_health(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "hello.txt"
    target.write_text("hello", encoding="utf-8")
    ui_dist = tmp_path / "ui" / "dist"
    ui_dist_assets = ui_dist / "assets"
    ui_dist_assets.mkdir(parents=True, exist_ok=True)
    (ui_dist / "index.html").write_text(
        "<!doctype html><html><body>st-ui-shell</body></html>",
        encoding="utf-8",
    )
    (ui_dist_assets / "app.js").write_text("console.log('st-asset');", encoding="utf-8")

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
        extra_env={"FILE_MCP_UI_DIST_PATH": str(ui_dist)},
    ):
        health = wait_for_health(f"http://127.0.0.1:{port}/health")
        assert health["status"] == "ok"
        runtime_config_url = f"http://127.0.0.1:{port}/runtime-config.js"
        with urlopen(runtime_config_url, timeout=2.0) as runtime_config_response:
            assert runtime_config_response.status == 200
            runtime_config_body = runtime_config_response.read().decode("utf-8")
        assert "window.__RUNTIME_CONFIG__" in runtime_config_body

        ui_url = f"http://127.0.0.1:{port}/ui"
        with urlopen(ui_url, timeout=2.0) as ui_response:
            assert ui_response.status == 200
            ui_body = ui_response.read().decode("utf-8")
        assert "st-ui-shell" in ui_body

        async def _unauthorized_call() -> None:
            async with Client(
                StreamableHttpTransport(f"http://127.0.0.1:{port}/mcp")
            ) as client:
                await client.call_tool("read_file", {"path": str(target)})

        with pytest.raises(Exception):
            asyncio.run(_unauthorized_call())

        async def _authorized_call() -> str:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool("read_file", {"path": str(target)})
                text_blocks = [
                    item.text for item in result.content if hasattr(item, "text")
                ]
                return "\n".join(text_blocks)

        text = asyncio.run(_authorized_call())
        assert "hello" in text
