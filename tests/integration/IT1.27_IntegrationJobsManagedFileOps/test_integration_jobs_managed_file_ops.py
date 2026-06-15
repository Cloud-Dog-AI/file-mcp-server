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

"""Managed jobs integration test for file processing.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Validates conversion operations are tracked as managed jobs over HTTP.
Requirements: FR1.21, FR1.23, NF1.3
Tasks: W28A-277
Architecture: 6. Interface Specifications, 8. Configuration Architecture
Tests: IT1.27
"""


from __future__ import annotations
import pytest

import asyncio
import json
from pathlib import Path
from tests.path_helpers import project_root
from urllib.request import Request, urlopen

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def _append_jobs_profile_config(path: Path) -> None:
    existing = path.read_text(encoding="utf-8")
    block = """
    server_id: "${FILE_MCP_SERVER_ID}"
    jobs:
      enabled: "${FILE_MCP_JOBS_ENABLED}"
      backend: "${FILE_MCP_JOBS_BACKEND}"
      queue_name: "${FILE_MCP_JOBS_QUEUE}"
      payload_max_bytes: "${FILE_MCP_JOBS_PAYLOAD_MAX_BYTES}"
      sql_url: "${FILE_MCP_JOBS_SQL_URL}"
      redis_url: "${FILE_MCP_JOBS_REDIS_URL}"
      redis_key_prefix: "${FILE_MCP_JOBS_REDIS_KEY_PREFIX}"
""".rstrip()
    if "jobs:" in existing and "FILE_MCP_JOBS_BACKEND" in existing:
        return
    marker = "    conversion:\n"
    patched = existing.replace(marker, f"{block}\n{marker}", 1)
    path.write_text(patched, encoding="utf-8")


def _http_get_json(url: str, *, auth_header_value: str) -> tuple[int, dict]:
    request = Request(
        url,
        method="GET",
        headers={"Authorization": auth_header_value},
    )
    with urlopen(request, timeout=3.0) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-008")


def test_conversion_operation_is_tracked_as_managed_job(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    source = root_dir / "doc.txt"
    source.write_text("integration jobs test", encoding="utf-8")
    output = root_dir / "doc.md"
    jobs_db = tmp_path / "jobs.db"

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    _append_jobs_profile_config(defaults_path)
    _append_jobs_profile_config(config_path)
    with env_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    "FILE_MCP_SERVER_ID=it-file-mcp-server-1",
                    "FILE_MCP_JOBS_ENABLED=true",
                    "FILE_MCP_JOBS_BACKEND=sql",
                    "FILE_MCP_JOBS_QUEUE=file-mcp-it",
                    "FILE_MCP_JOBS_PAYLOAD_MAX_BYTES=65536",
                    f"FILE_MCP_JOBS_SQL_URL=sqlite:///{jobs_db}",
                    "FILE_MCP_JOBS_REDIS_URL=",
                    "FILE_MCP_JOBS_REDIS_KEY_PREFIX=file_mcp_jobs_it",
                ]
            )
            + "\n"
        )

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=60.0)

        async def _convert() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                response = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(source),
                        "target_format": "md",
                        "output_path": str(output),
                        "backend": "builtin-text-copy",
                    },
                )
                return json.loads(
                    "\n".join(item.text for item in response.content if hasattr(item, "text"))
                )

        convert_payload = asyncio.run(_convert())
        assert convert_payload["ok"] is True
        assert "job_id" in convert_payload
        job_id = str(convert_payload["job_id"])

        status_code, get_payload = _http_get_json(
            f"http://127.0.0.1:{port}/api/v1/jobs/{job_id}",
            auth_header_value="Bearer secret",
        )
        assert status_code == 200
        assert get_payload["ok"] is True
        assert get_payload["job"]["job_id"] == job_id
        assert get_payload["job"]["status"] == "succeeded"

        status_code, list_payload = _http_get_json(
            f"http://127.0.0.1:{port}/api/v1/jobs?limit=10",
            auth_header_value="Bearer secret",
        )
        assert status_code == 200
        assert list_payload["ok"] is True
        assert any(item.get("job_id") == job_id for item in list_payload["jobs"])
