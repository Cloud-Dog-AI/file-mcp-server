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
from shutil import which
import zipfile

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def _write_minimal_docx(path: Path, *, text: str) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document)
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


@pytest.mark.skipif(which("pandoc") is None, reason="pandoc not installed")
def test_real_pandoc_backend_conversion(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    source = root_dir / "input.md"
    output = root_dir / "output.html"
    source.write_text("# Real Pandoc\ncontent\n", encoding="utf-8")

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

        async def _call() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(source),
                        "target_format": "html",
                        "output_path": str(output),
                        "backend": "pandoc",
                    },
                )
                return json.loads(
                    "\n".join(
                        item.text for item in result.content if hasattr(item, "text")
                    )
                )

        payload = asyncio.run(_call())
        assert payload["ok"] is True
        assert payload["backend"] == "pandoc"
        assert output.exists()
        assert "<h1" in output.read_text(encoding="utf-8").lower()
@pytest.mark.ST
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


@pytest.mark.skipif(which("soffice") is None, reason="soffice not installed")
def test_real_libreoffice_backend_conversion(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    source = root_dir / "input.docx"
    output = root_dir / "output.txt"
    _write_minimal_docx(source, text="Real LibreOffice")

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

        async def _call() -> dict:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                result = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(source),
                        "target_format": "txt",
                        "output_path": str(output),
                        "backend": "libreoffice",
                    },
                )
                return json.loads(
                    "\n".join(
                        item.text for item in result.content if hasattr(item, "text")
                    )
                )

        payload = asyncio.run(_call())
        assert payload["ok"] is True
        assert payload["backend"] == "libreoffice"
        assert output.exists()
