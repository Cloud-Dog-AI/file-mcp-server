from __future__ import annotations

import asyncio
import json
import os
import shutil
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


def test_conversion_backend_selection_and_fallback_metadata(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    src = root_dir / "doc.txt"
    src.write_text("hello", encoding="utf-8")
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
                selected = await client.call_tool(
                    "convert_file",
                    {
                        "path": str(src),
                        "target_format": "md",
                        "output_path": str(out),
                        "backend": "builtin-text-copy",
                    },
                )
                mismatched = await client.call_tool(
                    "convert_file",
                    {"path": str(src), "target_format": "md", "backend": "nonexistent-backend"},
                )
                selected_payload = json.loads("\n".join(item.text for item in selected.content if hasattr(item, "text")))
                mismatched_payload = json.loads("\n".join(item.text for item in mismatched.content if hasattr(item, "text")))
                return selected_payload, mismatched_payload

        selected_payload, mismatched_payload = asyncio.run(_calls())
        assert selected_payload["ok"] is True
        assert selected_payload["backend"] == "builtin-text-copy"
        assert selected_payload["used_fallback"] is False
        assert Path(selected_payload["output_path"]).exists()

        assert mismatched_payload["ok"] is False
        assert mismatched_payload["error_code"] == "unknown_backend"


def test_conversion_explicit_external_backend_when_available(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    src = root_dir / "doc.txt"
    src.write_text("hello external backend", encoding="utf-8")
    out = root_dir / "doc.md"

    repo_root = project_root(Path(__file__))
    bin_dir = repo_root / "working" / f"fake-bin-{port}"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_pandoc = bin_dir / "pandoc"
    fake_pandoc.write_text(
        "#!/bin/sh\n"
        "in=\"$1\"\n"
        "flag=\"$2\"\n"
        "out=\"$3\"\n"
        "if [ \"$flag\" != \"-o\" ]; then\n"
        "  exit 2\n"
        "fi\n"
        "cp \"$in\" \"$out\"\n",
        encoding="utf-8",
    )
    fake_pandoc.chmod(0o755)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    try:
        with running_server(
            repo_root,
            defaults_path=defaults_path,
            config_path=config_path,
            env_path=env_path,
            pidfile=pidfile,
            extra_env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
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
                            "path": str(src),
                            "target_format": "md",
                            "output_path": str(out),
                            "backend": "pandoc",
                        },
                    )
                    return json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))

            payload = asyncio.run(_call())
            assert payload["ok"] is True
            assert payload["backend"] == "pandoc"
            assert payload["used_fallback"] is False
            assert Path(payload["output_path"]).exists()
    finally:
        shutil.rmtree(bin_dir, ignore_errors=True)


def test_conversion_explicit_libreoffice_backend_when_available(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    src = root_dir / "sheet.docx"
    src.write_text("dummy office payload", encoding="utf-8")
    out = root_dir / "sheet.txt"

    repo_root = project_root(Path(__file__))
    bin_dir = repo_root / "working" / f"fake-soffice-{port}"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_soffice = bin_dir / "soffice"
    fake_soffice.write_text(
        "#!/bin/sh\n"
        "target=\"$3\"\n"
        "outdir=\"$5\"\n"
        "infile=\"$6\"\n"
        "stem=$(basename \"$infile\")\n"
        "stem=${stem%.*}\n"
        "cp \"$infile\" \"$outdir/$stem.$target\"\n",
        encoding="utf-8",
    )
    fake_soffice.chmod(0o755)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    try:
        with running_server(
            repo_root,
            defaults_path=defaults_path,
            config_path=config_path,
            env_path=env_path,
            pidfile=pidfile,
            extra_env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
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
                            "path": str(src),
                            "target_format": "txt",
                            "output_path": str(out),
                            "backend": "libreoffice",
                        },
                    )
                    return json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))

            payload = asyncio.run(_call())
            assert payload["ok"] is True
            assert payload["backend"] == "libreoffice"
            assert payload["used_fallback"] is False
            assert Path(payload["output_path"]).exists()
    finally:
        shutil.rmtree(bin_dir, ignore_errors=True)


def test_conversion_explicit_backend_unavailable_and_unsupported_codes(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    office_src = root_dir / "sheet.docx"
    office_src.write_text("dummy office payload", encoding="utf-8")
    text_src = root_dir / "doc.txt"
    text_src.write_text("hello", encoding="utf-8")

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
        extra_env={"PATH": ""},
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _calls() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                unavailable = await client.call_tool(
                    "convert_file",
                    {"path": str(office_src), "target_format": "txt", "backend": "libreoffice"},
                )
                unsupported = await client.call_tool(
                    "convert_file",
                    {"path": str(text_src), "target_format": "md", "backend": "pdf"},
                )
                unavailable_payload = json.loads(
                    "\n".join(item.text for item in unavailable.content if hasattr(item, "text"))
                )
                unsupported_payload = json.loads(
                    "\n".join(item.text for item in unsupported.content if hasattr(item, "text"))
                )
                return unavailable_payload, unsupported_payload

        unavailable_payload, unsupported_payload = asyncio.run(_calls())
        assert unavailable_payload["ok"] is False
        assert unavailable_payload["error_code"] == "backend_unavailable"
        assert unavailable_payload["backend"] == "libreoffice"

        assert unsupported_payload["ok"] is False
        assert unsupported_payload["error_code"] == "unsupported_format"
        assert unsupported_payload["backend"] == "pdf"
