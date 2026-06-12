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
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_structured_failed_mutation_is_rolled_back_and_audited(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "data.json"
    yaml_target = root_dir / "data.yaml"
    json_target.write_text('{"root":{"a":1}}', encoding="utf-8")
    yaml_target.write_text("root:\n  a: 1\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    json_before = json_target.read_text(encoding="utf-8")
    yaml_before = yaml_target.read_text(encoding="utf-8")

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _invalid_json_op() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "json_move_file",
                    {
                        "path": str(json_target),
                        "from_path": "/missing/path",
                        "to_path": "/root/b",
                    },
                )

        async def _invalid_yaml_op() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "yaml_copy_file",
                    {
                        "path": str(yaml_target),
                        "from_path": "/missing/path",
                        "to_path": "/root/b",
                    },
                )

        async def _invalid_json_type_mismatch() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "json_copy_file",
                    {
                        "path": str(json_target),
                        "from_path": "/root/a",
                        "to_path": "/root/a/b",
                    },
                )

        with pytest.raises(Exception):
            asyncio.run(_invalid_json_op())
        with pytest.raises(Exception):
            asyncio.run(_invalid_yaml_op())
        with pytest.raises(Exception):
            asyncio.run(_invalid_json_type_mismatch())

    assert json_target.read_text(encoding="utf-8") == json_before
    assert yaml_target.read_text(encoding="utf-8") == yaml_before

    lines = [
        line
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events = [json.loads(line) for line in lines]
    assert any(
        evt["tool"] == "json_move_file" and evt["status"] == "error" for evt in events
    )
    assert any(
        evt["tool"] == "yaml_copy_file" and evt["status"] == "error" for evt in events
    )
    assert any(
        evt["tool"] == "json_copy_file" and evt["status"] == "error" for evt in events
    )
