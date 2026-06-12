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
from tests.path_helpers import project_root

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_read_file_partial_line_and_byte_ranges(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "sample.txt"
    target.write_text("line1\nline2\nline3\n", encoding="utf-8")

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

        async def _calls() -> tuple[str, str]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                by_line = await client.call_tool(
                    "read_file",
                    {"path": str(target), "start_line": 2, "end_line": 3},
                )
                by_byte = await client.call_tool(
                    "read_file",
                    {"path": str(target), "start_byte": 0, "end_byte": 5},
                )
                line_payload = "\n".join(
                    item.text for item in by_line.content if hasattr(item, "text")
                )
                byte_payload = "\n".join(
                    item.text for item in by_byte.content if hasattr(item, "text")
                )
                return line_payload, byte_payload

        line_payload, byte_payload = asyncio.run(_calls())
        assert line_payload == "line2\nline3\n"
        assert byte_payload == "line1"
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_read_file_rejects_mixed_line_and_byte_ranges(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "sample.txt"
    target.write_text("line1\n", encoding="utf-8")

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

        async def _invalid_call() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "read_file",
                    {
                        "path": str(target),
                        "start_line": 1,
                        "end_line": 1,
                        "start_byte": 0,
                        "end_byte": 1,
                    },
                )

        with pytest.raises(ToolError, match="Cannot combine line and byte ranges"):
            asyncio.run(_invalid_call())
