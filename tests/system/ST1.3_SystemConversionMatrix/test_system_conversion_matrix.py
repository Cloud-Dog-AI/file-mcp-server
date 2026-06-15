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


def test_conversion_response_matrix_fields(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    text_input = root_dir / "doc.txt"
    text_input.write_text("hello", encoding="utf-8")
    bad_input = root_dir / "blob.bin"
    bad_input.write_bytes(b"\x00\x01")
    out = root_dir / "doc.md"

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
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _calls() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                success = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(text_input),
                        "target_format": "md",
                        "output_path": str(out),
                    },
                )
                failure = await client.call_tool(
                    "convert_file",
                    {"path": str(bad_input), "target_format": "txt"},
                    raise_on_error=False,
                )
                success_payload = json.loads(
                    "\n".join(
                        item.text for item in success.content if hasattr(item, "text")
                    )
                )
                failure_payload = json.loads(
                    "\n".join(
                        item.text for item in failure.content if hasattr(item, "text")
                    )
                )
                return success_payload, failure_payload

        success_payload, failure_payload = asyncio.run(_calls())
        assert success_payload["ok"] is True
        assert "backend" in success_payload
        assert "used_fallback" in success_payload
        assert "warnings" in success_payload
        assert Path(success_payload["output_path"]).exists()

        assert failure_payload["ok"] is False
        assert "backend" in failure_payload
        assert "used_fallback" in failure_payload
        assert "error_code" in failure_payload
        assert isinstance(failure_payload["warnings"], list)
