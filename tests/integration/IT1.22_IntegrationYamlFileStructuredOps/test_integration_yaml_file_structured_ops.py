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

import yaml
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
@pytest.mark.req("FR-029")


def test_yaml_file_structured_crud_with_audit_snapshot(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "data.yaml"
    target.write_text("root:\n  a: 1\n", encoding="utf-8")

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
                ops = [
                    (
                        "yaml_set_file",
                        {"path": str(target), "yaml_path": "/root/b", "value": 2},
                    ),  # create
                    (
                        "yaml_set_file",
                        {"path": str(target), "yaml_path": "/root/a", "value": 3},
                    ),  # update
                    (
                        "yaml_delete_file",
                        {"path": str(target), "yaml_path": "/root/b"},
                    ),  # delete
                ]
                for name, args in ops:
                    result = await client.call_tool(name, args)
                    payload = json.loads(
                        "\n".join(
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        )
                    )
                    assert payload["ok"] is True
                    assert payload["valid"] is True

        asyncio.run(_flow())

    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert data["root"]["a"] == 3
    assert "b" not in data["root"]

    snapshots_root = tmp_path / "snapshots"
    assert list(snapshots_root.rglob("data.yaml"))

    lines = [
        line
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    tools = [json.loads(line).get("tool") for line in lines]
    assert "yaml_set_file" in tools
    assert "yaml_delete_file" in tools
