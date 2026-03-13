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


def _decode_result(result):
    structured = getattr(result, "structuredContent", None)
    if structured not in (None, {}):
        return structured
    text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def test_iterative_search_update_retrieve_cycle_is_bounded_and_audited(
    tmp_path: Path,
) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    (root_dir / "level1" / "level2").mkdir(parents=True, exist_ok=True)
    target = root_dir / "level1" / "level2" / "cycle.txt"
    target.write_text("seed\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=500,
        search_max_file_mb=2,
        search_timeout_s=5,
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

        async def _cycle() -> str:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                for i in range(20):
                    update = _decode_result(
                        await client.call_tool(
                            "sed_edit_file",
                            {
                                "path": str(target),
                                "operations": [
                                    {
                                        "op": "insert_after_line",
                                        "line_no": 1,
                                        "content": f"line-{i} ✓ Δ",
                                    }
                                ],
                            },
                        )
                    )
                    assert update["ok"] is True

                    find = _decode_result(
                        await client.call_tool(
                            "search_content",
                            {
                                "query": "line-",
                                "max_depth": 2,
                                "timeout_s": 5,
                            },
                        )
                    )
                    assert find["matches"], (
                        "expected search matches during iterative flow"
                    )

                    read = _decode_result(
                        await client.call_tool(
                            "read_file",
                            {
                                "path": str(target),
                                "start_line": 1,
                                "end_line": 30,
                            },
                        )
                    )
                    assert f"line-{i}" in read

                depth_filtered = _decode_result(
                    await client.call_tool(
                        "search_paths",
                        {
                            "query": "cycle.txt",
                            "max_depth": 0,
                            "timeout_s": 5,
                        },
                    )
                )
                assert depth_filtered["matches"] == []

                depth_allowed = _decode_result(
                    await client.call_tool(
                        "search_paths",
                        {
                            "query": "cycle.txt",
                            "max_depth": 2,
                            "timeout_s": 5,
                        },
                    )
                )
                assert depth_allowed["matches"]

                final_text = _decode_result(
                    await client.call_tool("read_file", {"path": str(target)})
                )
                return final_text

        final_text = asyncio.run(asyncio.wait_for(_cycle(), timeout=30))

    assert "line-19" in final_text
    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sed_ok_events = [
        event
        for event in events
        if event.get("tool") == "sed_edit_file" and event.get("status") == "ok"
    ]
    assert len(sed_ok_events) >= 20
