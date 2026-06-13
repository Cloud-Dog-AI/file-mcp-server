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
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_application_multifile_transaction_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    file_a = root_dir / "service-a.txt"
    file_b = root_dir / "service-b.txt"
    file_a.write_text("status=TODO\nowner=alpha\n", encoding="utf-8")
    file_b.write_text("status=TODO\nowner=beta\n", encoding="utf-8")
    baseline_a = root_dir / "service-a.baseline.txt"
    baseline_b = root_dir / "service-b.baseline.txt"

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=20,
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

        async def _flow() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                for src, dst in ((file_a, baseline_a), (file_b, baseline_b)):
                    result = await client.call_tool(
                        "copy_file",
                        {"src": str(src), "dst": str(dst), "overwrite": True},
                    )
                    payload = json.loads(
                        "\n".join(
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        )
                    )
                    assert payload["ok"] is True

                for target in (file_a, file_b):
                    result = await client.call_tool(
                        "sed_edit_file",
                        {
                            "path": str(target),
                            "operations": [
                                {
                                    "op": "replace_regex",
                                    "pattern": "status=TODO",
                                    "repl": "status=DONE",
                                },
                                {
                                    "op": "insert_after_line",
                                    "line_no": 2,
                                    "content": "approved=true",
                                },
                            ],
                        },
                    )
                    payload = json.loads(
                        "\n".join(
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        )
                    )
                    assert payload["ok"] is True

                diff_a = await client.call_tool(
                    "diff_files", {"path_a": str(baseline_a), "path_b": str(file_a)}
                )
                diff_b = await client.call_tool(
                    "diff_files", {"path_a": str(baseline_b), "path_b": str(file_b)}
                )
                payload_a = json.loads(
                    "\n".join(
                        item.text for item in diff_a.content if hasattr(item, "text")
                    )
                )
                payload_b = json.loads(
                    "\n".join(
                        item.text for item in diff_b.content if hasattr(item, "text")
                    )
                )
                return payload_a, payload_b

        diff_a_payload, diff_b_payload = asyncio.run(_flow())
        assert diff_a_payload["ok"] is True
        assert diff_b_payload["ok"] is True
        assert "-status=TODO" in diff_a_payload["diff"]
        assert "+status=DONE" in diff_a_payload["diff"]
        assert "+approved=true" in diff_a_payload["diff"]
        assert "-status=TODO" in diff_b_payload["diff"]
        assert "+status=DONE" in diff_b_payload["diff"]
        assert "+approved=true" in diff_b_payload["diff"]

    assert "status=DONE" in file_a.read_text(encoding="utf-8")
    assert "status=DONE" in file_b.read_text(encoding="utf-8")
    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sed_events = [
        evt
        for evt in events
        if evt.get("tool") == "sed_edit_file" and evt.get("status") == "ok"
    ]
    assert len(sed_events) >= 2
