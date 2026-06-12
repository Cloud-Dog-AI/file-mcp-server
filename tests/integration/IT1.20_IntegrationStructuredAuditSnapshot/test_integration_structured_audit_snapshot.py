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
import pytest
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_structured_edit_with_audit_and_snapshot(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "data.json"
    target.write_text('{"a": 1, "nested": {"x": 1}}', encoding="utf-8")

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
                result = await client.call_tool(
                    "json_set_file",
                    {"path": str(target), "json_path": "/nested/x", "value": 42},
                )
                structured = getattr(result, "structuredContent", None) or {}
                if structured:
                    return structured
                text_blocks = [
                    item.text for item in result.content if hasattr(item, "text")
                ]
                if text_blocks:
                    try:
                        parsed = json.loads("\n".join(text_blocks))
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
                return {}

        structured = asyncio.run(_flow())
        assert structured.get("ok") is True
        assert structured.get("valid") is True

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["nested"]["x"] == 42

        snapshots_root = tmp_path / "snapshots"
        snapshot_files = list(snapshots_root.rglob("data.json"))
        assert snapshot_files, "expected snapshot file for pre-change content"
        assert (
            json.loads(snapshot_files[0].read_text(encoding="utf-8"))["nested"]["x"]
            == 1
        )

        assert audit_log.exists()
        lines = [
            line
            for line in audit_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert lines, "expected audit entries"
        event = json.loads(lines[-1])
        assert event["tool"] == "json_set_file"
        assert event["status"] == "ok"
