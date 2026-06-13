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

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root
import pytest


def _call_mcp_tool(
    *, base_url: str, request_id: int, tool_name: str, arguments: dict
) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    request = Request(
        f"{base_url}/mcp",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")
    request.add_header("Authorization", "Bearer secret")
    with urlopen(request, timeout=5.0) as response:
        raw_body = response.read().decode("utf-8")
    if "data:" in raw_body:
        sse_data = []
        for line in raw_body.splitlines():
            if line.startswith("data:"):
                sse_data.append(line[len("data:") :].strip())
        envelope = json.loads("\n".join(sse_data))
    else:
        envelope = json.loads(raw_body)
    if envelope.get("error"):
        raise RuntimeError(f"MCP error: {envelope['error']}")
    result = envelope.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected MCP result envelope: {result!r}")

    content_items = result.get("content")
    if isinstance(content_items, list):
        text_parts = [
            str(item.get("text"))
            for item in content_items
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if text_parts:
            payload_text = "\n".join(text_parts)
            decoded = json.loads(payload_text)
            if not isinstance(decoded, dict):
                raise RuntimeError(f"Unexpected tool payload: {decoded!r}")
            return decoded

    return result


def _to_zulu(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _match_paths(payload: dict) -> set[str]:
    return {str(item.get("path")) for item in payload.get("matches") or []}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_st1_18_time_based_search_filters_honor_modified_window(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "w28a510-time-filter.txt"
    marker = f"w28a510-time-filter-{int(datetime.now(tz=timezone.utc).timestamp())}"

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=25,
    )

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        base_url = f"http://127.0.0.1:{port}"
        wait_for_health(f"{base_url}/health")

        _call_mcp_tool(
            base_url=base_url,
            request_id=1,
            tool_name="write_file",
            arguments={"path": str(target), "content": f"{marker}\n"},
        )
        now = datetime.now(tz=timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        one_hour_future = now + timedelta(hours=1)
        one_minute_future = now + timedelta(minutes=1)
        try:
            after_past = _call_mcp_tool(
                base_url=base_url,
                request_id=2,
                tool_name="search_content",
                arguments={
                    "query": marker,
                    "modified_after": _to_zulu(one_hour_ago),
                },
            )
            after_future = _call_mcp_tool(
                base_url=base_url,
                request_id=3,
                tool_name="search_content",
                arguments={
                    "query": marker,
                    "modified_after": _to_zulu(one_hour_future),
                },
            )
            before_future = _call_mcp_tool(
                base_url=base_url,
                request_id=4,
                tool_name="search_content",
                arguments={
                    "query": marker,
                    "modified_before": _to_zulu(one_minute_future),
                },
            )
            before_past = _call_mcp_tool(
                base_url=base_url,
                request_id=5,
                tool_name="search_content",
                arguments={
                    "query": marker,
                    "modified_before": _to_zulu(one_hour_ago),
                },
            )
        finally:
            _call_mcp_tool(
                base_url=base_url,
                request_id=6,
                tool_name="delete_file",
                arguments={"path": str(target), "missing_ok": True},
            )

    target_path = str(target)
    assert target_path in _match_paths(after_past)
    assert target_path not in _match_paths(after_future)
    assert target_path in _match_paths(before_future)
    assert target_path not in _match_paths(before_past)
