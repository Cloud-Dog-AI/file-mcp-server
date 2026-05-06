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


def _decode_result(result):
    # Extract text from content blocks first (works with both old and new fastmcp)
    text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


@pytest.mark.parametrize(
    "variant",
    [
        {
            "name": "default-bearer-single-key",
            "api_keys": ["secret-a"],
            "header_name": "Authorization",
            "header_scheme": "Bearer",
            "allow_globs": ["**/*"],
            "deny_globs": [],
        },
        {
            "name": "custom-header-rotated-key",
            "api_keys": ["alpha", "beta"],
            "header_name": "X-Api-Key",
            "header_scheme": "Token",
            "allow_globs": ["**/*"],
            "deny_globs": [],
        },
        {
            "name": "scoped-with-deny",
            "api_keys": ["scoped"],
            "header_name": "Authorization",
            "header_scheme": "Bearer",
            "allow_globs": ["**/*"],
            "deny_globs": ["**/allowed/private/**"],
        },
    ],
)
def test_config_matrix_harness_validates_scope_limits_auth_and_audit(
    tmp_path: Path, variant: dict
) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    (root_dir / "allowed" / "private").mkdir(parents=True, exist_ok=True)
    (root_dir / "allowed" / "public").mkdir(parents=True, exist_ok=True)

    public_file = root_dir / "allowed" / "public" / "data.txt"
    private_file = root_dir / "allowed" / "private" / "secret.txt"

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        api_keys=variant["api_keys"],
        auth_header_name=variant["header_name"],
        auth_header_scheme=variant["header_scheme"],
        allow_globs=variant["allow_globs"],
        deny_globs=variant["deny_globs"],
        search_max_results=5,
        search_max_file_mb=1,
        search_timeout_s=5,
    )
    repo_root = project_root(Path(__file__))

    auth_value = f"{variant['header_scheme']} {variant['api_keys'][-1]}"
    header_name = variant["header_name"]

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
                    headers={header_name: auth_value},
                )
            ) as client:
                write_payload = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(public_file), "content": "matrix-text-✓"},
                    )
                )
                assert write_payload["ok"] is True

                search_payload = _decode_result(
                    await client.call_tool(
                        "search_content",
                        {"query": "matrix-text", "max_depth": 3, "timeout_s": 5},
                    )
                )
                read_payload = _decode_result(
                    await client.call_tool("read_file", {"path": str(public_file)})
                )

                deny_result = None
                if variant["deny_globs"]:
                    (root_dir / "allowed" / "private").mkdir(
                        parents=True, exist_ok=True
                    )
                    private_file.write_text("secret", encoding="utf-8")
                    with pytest.raises(Exception):
                        await client.call_tool("read_file", {"path": str(private_file)})
                    deny_result = "blocked"

                delete_payload = _decode_result(
                    await client.call_tool("delete_file", {"path": str(public_file)})
                )
                return {
                    "search": search_payload,
                    "read": read_payload,
                    "delete": delete_payload,
                    "deny": deny_result,
                }

        payload = asyncio.run(_flow())

    assert payload["search"]["matches"]
    assert "matrix-text-✓" in payload["read"]
    assert payload["delete"]["ok"] is True
    if variant["deny_globs"]:
        assert payload["deny"] == "blocked"

    entries = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert entries
    assert any(
        entry.get("tool") == "write_file" and entry.get("status") == "ok"
        for entry in entries
    )
    assert any(
        entry.get("tool") == "delete_file" and entry.get("status") == "ok"
        for entry in entries
    )
