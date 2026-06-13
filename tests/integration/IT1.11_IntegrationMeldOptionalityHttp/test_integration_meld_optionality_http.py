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
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_meld_optional_unavailable_returns_warning(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    left = root_dir / "left.txt"
    right = root_dir / "right.txt"
    left.write_text("one\n", encoding="utf-8")
    right.write_text("two\n", encoding="utf-8")

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
        extra_env={"PATH": ""},
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _call() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "meld_files",
                    {"path_a": str(left), "path_b": str(right)},
                    raise_on_error=False,
                )
                data = getattr(result, "data", None)
                if isinstance(data, dict):
                    return data
                text = "\n".join(
                    item.text for item in result.content if hasattr(item, "text")
                )
                return json.loads(text)

        payload = asyncio.run(_call())
        assert payload["ok"] is False
        assert payload["path_a"] == str(left)
        assert payload["path_b"] == str(right)
        assert payload["warnings"]
        assert "not available" in payload["warnings"][0]
