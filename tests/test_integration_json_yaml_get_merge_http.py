from __future__ import annotations

import asyncio
import json
from pathlib import Path

import yaml
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_json_yaml_file_level_operation_matrix_depth(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "data.json"
    yaml_target = root_dir / "data.yaml"
    json_target.write_text('{"root":{"a":1}}', encoding="utf-8")
    yaml_target.write_text("root:\n  a: 1\n", encoding="utf-8")

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    repo_root = Path(__file__).resolve().parents[1]
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _flow() -> tuple[dict, dict]:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                create = await client.call_tool(
                    "json_set_file",
                    {"path": str(json_target), "json_path": "/root/b", "value": 2},
                )
                create_payload = json.loads("\n".join(item.text for item in create.content if hasattr(item, "text")))
                assert create_payload["ok"] is True
                assert create_payload["valid"] is True

                extracted = await client.call_tool(
                    "json_get_file",
                    {"path": str(json_target), "json_path": "/root/b"},
                )
                extracted_payload = json.loads(
                    "\n".join(item.text for item in extracted.content if hasattr(item, "text"))
                )

                json_copy = await client.call_tool(
                    "json_copy_file",
                    {"path": str(json_target), "from_path": "/root/b", "to_path": "/root/copy_b"},
                )
                json_copy_payload = json.loads(
                    "\n".join(item.text for item in json_copy.content if hasattr(item, "text"))
                )
                assert json_copy_payload["ok"] is True

                json_move = await client.call_tool(
                    "json_move_file",
                    {"path": str(json_target), "from_path": "/root/copy_b", "to_path": "/root/moved_b"},
                )
                json_move_payload = json.loads(
                    "\n".join(item.text for item in json_move.content if hasattr(item, "text"))
                )
                assert json_move_payload["ok"] is True

                json_merge = await client.call_tool(
                    "json_merge_file",
                    {"path": str(json_target), "json_path": "/root", "value": {"nested": {"x": 7}}},
                )
                json_merge_payload = json.loads(
                    "\n".join(item.text for item in json_merge.content if hasattr(item, "text"))
                )
                assert json_merge_payload["ok"] is True

                merge = await client.call_tool(
                    "yaml_merge_file",
                    {"path": str(yaml_target), "value": {"root": {"b": 2, "nested": {"x": 9}}}},
                )
                merge_payload = json.loads("\n".join(item.text for item in merge.content if hasattr(item, "text")))
                assert merge_payload["ok"] is True
                assert merge_payload["valid"] is True

                read_merged = await client.call_tool(
                    "yaml_get_file",
                    {"path": str(yaml_target), "yaml_path": "/root/nested/x"},
                )
                read_merged_payload = json.loads(
                    "\n".join(item.text for item in read_merged.content if hasattr(item, "text"))
                )

                yaml_copy = await client.call_tool(
                    "yaml_copy_file",
                    {"path": str(yaml_target), "from_path": "/root/a", "to_path": "/root/copy_a"},
                )
                yaml_copy_payload = json.loads(
                    "\n".join(item.text for item in yaml_copy.content if hasattr(item, "text"))
                )
                assert yaml_copy_payload["ok"] is True

                yaml_move = await client.call_tool(
                    "yaml_move_file",
                    {"path": str(yaml_target), "from_path": "/root/copy_a", "to_path": "/root/moved_a"},
                )
                yaml_move_payload = json.loads(
                    "\n".join(item.text for item in yaml_move.content if hasattr(item, "text"))
                )
                assert yaml_move_payload["ok"] is True

                delete = await client.call_tool(
                    "yaml_delete_file",
                    {"path": str(yaml_target), "yaml_path": "/root/b"},
                )
                delete_payload = json.loads("\n".join(item.text for item in delete.content if hasattr(item, "text")))
                assert delete_payload["ok"] is True
                assert delete_payload["valid"] is True

                return extracted_payload, read_merged_payload

        extracted_payload, read_merged_payload = asyncio.run(_flow())
        assert extracted_payload["ok"] is True
        assert extracted_payload["value"] == 2
        assert read_merged_payload["ok"] is True
        assert read_merged_payload["value"] == 9

    json_doc = json.loads(json_target.read_text(encoding="utf-8"))
    yaml_doc = yaml.safe_load(yaml_target.read_text(encoding="utf-8"))
    assert json_doc["root"]["b"] == 2
    assert json_doc["root"]["moved_b"] == 2
    assert json_doc["root"]["nested"]["x"] == 7
    assert yaml_doc["root"]["a"] == 1
    assert yaml_doc["root"]["moved_a"] == 1
    assert yaml_doc["root"]["nested"]["x"] == 9
    assert "b" not in yaml_doc["root"]
