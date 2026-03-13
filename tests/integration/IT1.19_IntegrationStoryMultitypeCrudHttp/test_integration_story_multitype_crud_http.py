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
import base64
import json
from pathlib import Path
from tests.path_helpers import project_root

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

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


def _write_pdf(path: Path, text: str) -> None:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream = f"BT\n/F1 14 Tf\n72 720 Td\n({escaped}) Tj\nET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content_stream.encode('latin-1'))} >>\nstream\n{content_stream}endstream".encode(
            "latin-1"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("ascii"))
        parts.append(obj)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    path.write_bytes(b"".join(parts))


def test_story_multitype_upload_search_update_retrieve_delete_with_audit(
    tmp_path: Path,
) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "txt": root_dir / "notes.txt",
        "json": root_dir / "data.json",
        "yaml": root_dir / "data.yaml",
        "xml": root_dir / "data.xml",
        "html": root_dir / "page.html",
        "md": root_dir / "doc.md",
        "bin": root_dir / "blob.bin",
    }

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        search_max_results=50,
        search_max_file_mb=2,
        search_timeout_s=10,
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

        async def _flow() -> tuple[dict, str, str, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                # Upload / create across text + structured + binary.
                for path, content in [
                    (paths["txt"], "Start UTF-8: café naïve — Δelta — 😀\n"),
                    (paths["json"], '{"title":"draft","count":1}'),
                    (paths["yaml"], "title: draft\ncount: 1\n"),
                    (paths["xml"], "<root><item>draft</item></root>"),
                    (paths["html"], "<html><body><p>draft</p></body></html>"),
                    (paths["md"], "---\ntitle: Draft\n---\n# Top\n## Child\nold\n"),
                ]:
                    result = await client.call_tool(
                        "write_file",
                        {"path": str(path), "content": content},
                    )
                    payload = _decode_result(result)
                    assert payload["ok"] is True

                b64_upload = await client.call_tool(
                    "b64_decode_to_file",
                    {
                        "path": str(paths["bin"]),
                        "data": base64.b64encode(b"binary\\x00payload").decode("ascii"),
                    },
                )
                b64_upload_payload = _decode_result(b64_upload)
                assert b64_upload_payload["ok"] is True

                # Search with depth and timeout controls.
                search_payload = _decode_result(
                    await client.call_tool(
                        "search_content",
                        {"query": "Δelta", "max_depth": 2, "timeout_s": 10},
                    )
                )
                assert search_payload["matches"]

                # Update all structured types.
                assert (
                    _decode_result(
                        await client.call_tool(
                            "json_set_file",
                            {
                                "path": str(paths["json"]),
                                "json_path": "/title",
                                "value": "released",
                            },
                        )
                    )["ok"]
                    is True
                )
                assert (
                    _decode_result(
                        await client.call_tool(
                            "yaml_set_file",
                            {
                                "path": str(paths["yaml"]),
                                "yaml_path": "/title",
                                "value": "released",
                            },
                        )
                    )["ok"]
                    is True
                )
                assert (
                    _decode_result(
                        await client.call_tool(
                            "xml_set_file",
                            {
                                "path": str(paths["xml"]),
                                "xpath": "/root/item",
                                "value": "released",
                            },
                        )
                    )["ok"]
                    is True
                )
                assert (
                    _decode_result(
                        await client.call_tool(
                            "html_set_file",
                            {
                                "path": str(paths["html"]),
                                "selector": "p",
                                "value": "released",
                            },
                        )
                    )["ok"]
                    is True
                )
                assert (
                    _decode_result(
                        await client.call_tool(
                            "markdown_set_section_file",
                            {
                                "path": str(paths["md"]),
                                "heading": ["Top", "Child"],
                                "new_content": "## Child\\nreleased",
                            },
                        )
                    )["ok"]
                    is True
                )
                assert (
                    _decode_result(
                        await client.call_tool(
                            "markdown_set_frontmatter_file",
                            {
                                "path": str(paths["md"]),
                                "updates": {"status": "released"},
                            },
                        )
                    )["ok"]
                    is True
                )

                retrieved_md = _decode_result(
                    await client.call_tool("read_file", {"path": str(paths["md"])})
                )
                retrieved_txt = _decode_result(
                    await client.call_tool("read_file", {"path": str(paths["txt"])})
                )
                b64_download = _decode_result(
                    await client.call_tool(
                        "b64_encode_file", {"path": str(paths["bin"])}
                    )
                )

                delete_payload = _decode_result(
                    await client.call_tool("delete_file", {"path": str(paths["txt"])})
                )
                assert delete_payload["ok"] is True

                return search_payload, retrieved_md, retrieved_txt, b64_download

        search_payload, retrieved_md, retrieved_txt, b64_download = asyncio.run(_flow())

    assert any("notes.txt" in match["path"] for match in search_payload["matches"])
    assert "released" in retrieved_md
    assert "café" in retrieved_txt
    assert b64_download["ok"] is True
    assert base64.b64decode(b64_download["data"]) == b"binary\\x00payload"
    assert not paths["txt"].exists()

    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events
    tool_names = {event.get("tool") for event in events}
    for expected_tool in {
        "write_file",
        "b64_decode_to_file",
        "json_set_file",
        "yaml_set_file",
        "xml_set_file",
        "html_set_file",
        "markdown_set_section_file",
        "markdown_set_frontmatter_file",
        "delete_file",
    }:
        assert expected_tool in tool_names
    assert all(event.get("status") in {"ok", "error"} for event in events)

    server_log = tmp_path / "server.log"
    if server_log.exists():
        assert server_log.read_text(encoding="utf-8")


def test_story_upload_pdf_convert_update_find_return_with_audit(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = root_dir / "report.pdf"
    converted_md = root_dir / "report-from-pdf.md"
    _write_pdf(pdf_path, "Report Cycle token Omega")

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
                from_pdf = _decode_result(
                    await client.call_tool(
                        "convert_file",
                        {
                            "path": str(pdf_path),
                            "target_format": "md",
                            "output_path": str(converted_md),
                        },
                    )
                )
                assert from_pdf["ok"] is True

                update_payload = _decode_result(
                    await client.call_tool(
                        "markdown_set_section_file",
                        {
                            "path": str(converted_md),
                            "heading": "report cycle token omega",
                            "new_content": "# Report\nCycle token: Omega updated",
                        },
                    )
                )
                assert update_payload["ok"] is True

                find_payload = _decode_result(
                    await client.call_tool("search_content", {"query": "Omega updated"})
                )
                read_payload = _decode_result(
                    await client.call_tool("read_file", {"path": str(converted_md)})
                )
                delete_payload = _decode_result(
                    await client.call_tool("delete_file", {"path": str(converted_md)})
                )
                assert delete_payload["ok"] is True
                return {"find": find_payload, "read": read_payload}

        payload = asyncio.run(_flow())

    assert payload["find"]["matches"]
    assert "Omega updated" in payload["read"]
    assert not converted_md.exists()

    events = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(event.get("tool") == "markdown_set_section_file" for event in events)


def test_upload_download_cycle_with_invalid_key_rejected(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "download.bin"

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        api_keys=["primary-secret", "rotated-secret"],
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

        async def _flow() -> str:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer rotated-secret"},
                )
            ) as client:
                encoded = base64.b64encode("naïve-✓".encode("utf-8")).decode("ascii")
                upload_payload = _decode_result(
                    await client.call_tool(
                        "b64_decode_to_file",
                        {"path": str(target), "data": encoded},
                    )
                )
                assert upload_payload["ok"] is True
                download_payload = _decode_result(
                    await client.call_tool("b64_encode_file", {"path": str(target)})
                )
                assert download_payload["ok"] is True
                return base64.b64decode(download_payload["data"]).decode("utf-8")

        value = asyncio.run(_flow())
        assert value == "naïve-✓"

        async def _bad_key() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer wrong-key"},
                )
            ) as client:
                await client.call_tool("read_file", {"path": str(target)})

        with pytest.raises((ToolError, httpx.HTTPStatusError)):
            asyncio.run(_bad_key())
