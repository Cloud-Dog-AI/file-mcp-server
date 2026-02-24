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


def test_base64_file_roundtrip_over_http(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    src = root_dir / "src.bin"
    dst = root_dir / "dst.bin"
    src.write_bytes(b"\x00hello\xff")

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

        async def _flow() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                enc = await client.call_tool("b64_encode_file", {"path": str(src)})
                enc_payload = json.loads("\n".join(item.text for item in enc.content if hasattr(item, "text")))
                assert enc_payload["ok"] is True
                data = enc_payload["data"]

                dec = await client.call_tool("b64_decode_to_file", {"path": str(dst), "data": data})
                dec_payload = json.loads("\n".join(item.text for item in dec.content if hasattr(item, "text")))
                assert dec_payload["ok"] is True

        asyncio.run(_flow())

    assert dst.read_bytes() == src.read_bytes()
