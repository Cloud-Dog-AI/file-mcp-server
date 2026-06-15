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
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.req("FR-028")


def test_error_contract_for_expected_operational_failures(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    too_large = root_dir / "large.md"
    too_large.write_text("x" * (2 * 1024 * 1024), encoding="utf-8")
    unsupported = root_dir / "blob.bin"
    unsupported.write_bytes(b"\x00\x01")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        conversion_max_input_mb=1,
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

        async def _calls() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                large_result = await client.call_tool(
                    "convert_file",
                    {"path": str(too_large), "target_format": "txt"},
                    raise_on_error=False,
                )
                unsupported_result = await client.call_tool(
                    "convert_file",
                    {"path": str(unsupported), "target_format": "txt"},
                    raise_on_error=False,
                )
                large_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in large_result.content
                        if hasattr(item, "text")
                    )
                )
                unsupported_payload = json.loads(
                    "\n".join(
                        item.text
                        for item in unsupported_result.content
                        if hasattr(item, "text")
                    )
                )
                return large_payload, unsupported_payload

        large_payload, unsupported_payload = asyncio.run(_calls())
        for payload in (large_payload, unsupported_payload):
            assert "ok" in payload
            assert "warnings" in payload
            assert payload["ok"] is False
            assert isinstance(payload["warnings"], list)
