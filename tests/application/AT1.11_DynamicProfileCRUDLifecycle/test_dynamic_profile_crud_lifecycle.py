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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root


def _result_text(result: Any) -> str:
    content = getattr(result, "content", [])
    return "".join(str(getattr(item, "text", "")) for item in content)


def _result_json(result: Any) -> dict[str, Any]:
    text = _result_text(result).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {"text": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


async def _call_tool(
    client: Client, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    payload = _result_json(result)
    ok = payload.get("ok")
    if ok is False:
        raise RuntimeError(f"CRITICAL ERROR: file-mcp tool '{tool}' failed: {payload}")
    return payload


async def _safe_delete_file(client: Client, path: str) -> None:
    try:
        await _call_tool(client, "delete_file", {"path": path})
    except Exception:
        return


async def _safe_delete_dir(client: Client, path: str) -> None:
    try:
        await _call_tool(client, "delete_file", {"path": path, "missing_ok": True})
    except Exception:
        return


def _is_present(matches: list[str], expected_path: str) -> bool:
    expected = expected_path.strip()
    for item in matches:
        candidate = str(item or "").strip()
        if not candidate:
            continue
        if candidate == expected:
            return True
        if candidate.endswith(Path(expected).name):
            return True
    return False


def test_at1_11_dynamic_profile_crud_lifecycle(tmp_path: Path) -> None:
    """AT1.11 dynamic profile/file lifecycle.

    Required env keys:
    - --env must be supplied (enforced by test harness).

    Note:
    file-mcp's current runtime contract does not expose REST profile/user/key CRUD
    endpoints. This AT validates the equivalent lifecycle using a dynamically
    provisioned runtime profile root and dynamic API keys in an isolated process.
    """

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    project_name = f"w26a-test-{stamp}"
    admin_key = f"w26a-admin-{stamp}"
    user_key = f"w26a-user-{stamp}"

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    profile_root = tmp_path / "profile_root" / project_name
    profile_root.mkdir(parents=True, exist_ok=True)

    port = pick_free_port()
    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        runtime_dir,
        port=port,
        root_dir=profile_root,
        api_keys=[admin_key, user_key],
    )

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        health = wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=20.0)
        assert health.get("status") == "ok"

        async def _workflow() -> None:
            created_files: list[str] = []
            created_dirs: list[str] = []

            transport = StreamableHttpTransport(
                f"http://127.0.0.1:{port}/mcp",
                headers={
                    "Authorization": f"Bearer {user_key}",
                    "X-File-MCP-Profile": "default",
                },
            )
            async with Client(transport) as client:
                tools = await client.list_tools()
                available = {str(tool.name or "") for tool in tools}
                for required in {
                    "create_dir",
                    "write_file",
                    "read_file",
                    "search_paths",
                    "delete_file",
                }:
                    assert required in available, (
                        f"Missing required file-mcp tool: {required}"
                    )

                date_folder = date.today().isoformat()
                scoped_dir = str(profile_root / date_folder)
                markdown_path = str(profile_root / date_folder / f"w26a-{stamp}.md")
                pdf_path = str(profile_root / date_folder / f"w26a-{stamp}.pdf")

                try:
                    await _call_tool(
                        client,
                        "create_dir",
                        {"path": scoped_dir, "parents": True, "exist_ok": True},
                    )
                    created_dirs.append(scoped_dir)

                    md_content = (
                        "# W26A Dynamic Profile Lifecycle\n\n"
                        "This markdown file is created by AT1.11.\n\n"
                        "## Searchable Paragraph\n"
                        "The quick brown fox validates searchable content in file-mcp.\n\n"
                        "```python\n"
                        "def marker() -> str:\n"
                        "    return 'AT1.11'\n"
                        "```\n"
                    )
                    await _call_tool(
                        client,
                        "write_file",
                        {
                            "path": markdown_path,
                            "content": md_content,
                            "overwrite": True,
                        },
                    )
                    created_files.append(markdown_path)

                    pdf_content = (
                        "%PDF-1.1\n"
                        "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                        "2 0 obj<</Type/Pages/Count 0>>endobj\n"
                        "trailer<</Root 1 0 R>>\n%%EOF\n"
                    )
                    await _call_tool(
                        client,
                        "write_file",
                        {"path": pdf_path, "content": pdf_content, "overwrite": True},
                    )
                    created_files.append(pdf_path)

                    md_read = await _call_tool(
                        client, "read_file", {"path": markdown_path}
                    )
                    current = str(md_read.get("content") or md_read.get("text") or "")
                    appended = (
                        current + "\n\n## Appended\nAdded by AT1.11 append phase.\n"
                    )
                    await _call_tool(
                        client,
                        "write_file",
                        {"path": markdown_path, "content": appended, "overwrite": True},
                    )

                    verify_read = await _call_tool(
                        client, "read_file", {"path": markdown_path}
                    )
                    verify_text = str(
                        verify_read.get("content") or verify_read.get("text") or ""
                    )
                    assert "Added by AT1.11 append phase" in verify_text

                    md_search = await _call_tool(
                        client,
                        "search_paths",
                        {"query": Path(markdown_path).name},
                    )
                    md_matches = [
                        str(item) for item in (md_search.get("matches") or [])
                    ]
                    assert _is_present(md_matches, markdown_path)

                    pdf_search = await _call_tool(
                        client,
                        "search_paths",
                        {"query": Path(pdf_path).name},
                    )
                    pdf_matches = [
                        str(item) for item in (pdf_search.get("matches") or [])
                    ]
                    assert _is_present(pdf_matches, pdf_path)
                finally:
                    for path in reversed(created_files):
                        await _safe_delete_file(client, path)
                    for path in reversed(created_dirs):
                        await _safe_delete_dir(client, path)

                assert not Path(markdown_path).exists(), (
                    f"Teardown left file: {markdown_path}"
                )
                assert not Path(pdf_path).exists(), f"Teardown left file: {pdf_path}"

        asyncio.run(_workflow())
