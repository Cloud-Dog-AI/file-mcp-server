from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)


def test_structured_path_edge_cases_and_negative_contract(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "edge.json"
    yaml_target = root_dir / "edge.yaml"
    json_target.write_text('{"a":{"b":1},"c":{}}', encoding="utf-8")
    yaml_target.write_text("a:\n  b: 1\nc: {}\n", encoding="utf-8")

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

        async def _valid_matrix() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                calls = [
                    ("json_copy_file", {"path": str(json_target), "from_path": "/a/b", "to_path": "/c/copied"}),
                    ("json_move_file", {"path": str(json_target), "from_path": "/c/copied", "to_path": "/a/moved"}),
                    ("json_merge_file", {"path": str(json_target), "json_path": "/a", "value": {"nested": {"x": 7}}}),
                    ("yaml_copy_file", {"path": str(yaml_target), "from_path": "/a/b", "to_path": "/c/copied"}),
                    ("yaml_move_file", {"path": str(yaml_target), "from_path": "/c/copied", "to_path": "/a/moved"}),
                    ("yaml_merge_file", {"path": str(yaml_target), "yaml_path": "/a", "value": {"nested": {"x": 9}}}),
                ]
                for name, args in calls:
                    result = await client.call_tool(name, args)
                    payload = json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))
                    assert payload["ok"] is True
                    assert payload["valid"] is True

        asyncio.run(_valid_matrix())

        json_before_negative = json_target.read_text(encoding="utf-8")
        yaml_before_negative = yaml_target.read_text(encoding="utf-8")

        async def _negative_calls() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "json_copy_file",
                    {"path": str(json_target), "from_path": "/missing/path", "to_path": "/z"},
                )

        with pytest.raises(Exception):
            asyncio.run(_negative_calls())

        async def _negative_calls_yaml() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "yaml_move_file",
                    {"path": str(yaml_target), "from_path": "/missing/path", "to_path": "/z"},
                )

        with pytest.raises(Exception):
            asyncio.run(_negative_calls_yaml())

        assert json_target.read_text(encoding="utf-8") == json_before_negative
        assert yaml_target.read_text(encoding="utf-8") == yaml_before_negative

    final_json = json.loads(json_target.read_text(encoding="utf-8"))
    final_yaml = yaml.safe_load(yaml_target.read_text(encoding="utf-8"))
    assert final_json["a"]["moved"] == 1
    assert final_json["a"]["nested"]["x"] == 7
    assert final_yaml["a"]["moved"] == 1
    assert final_yaml["a"]["nested"]["x"] == 9


def test_structured_nested_list_dict_and_root_merge_paths(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    json_target = root_dir / "nested.json"
    yaml_target = root_dir / "nested.yaml"
    json_target.write_text(
        '{"root":{"items":[{"id":1},{"id":2}]},"meta":{}}',
        encoding="utf-8",
    )
    yaml_target.write_text(
        "root:\n  items:\n    - id: 1\n    - id: 2\nmeta: {}\n",
        encoding="utf-8",
    )

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

        async def _valid_ops() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                calls = [
                    (
                        "json_copy_file",
                        {"path": str(json_target), "from_path": "/root/items/0/id", "to_path": "/meta/first_id"},
                    ),
                    (
                        "json_move_file",
                        {"path": str(json_target), "from_path": "/root/items/1/id", "to_path": "/root/items/0/second_id"},
                    ),
                    (
                        "json_merge_file",
                        {"path": str(json_target), "value": {"meta": {"status": "ok"}}},
                    ),
                    (
                        "yaml_copy_file",
                        {"path": str(yaml_target), "from_path": "/root/items/0/id", "to_path": "/meta/first_id"},
                    ),
                    (
                        "yaml_move_file",
                        {"path": str(yaml_target), "from_path": "/root/items/1/id", "to_path": "/root/items/0/second_id"},
                    ),
                    (
                        "yaml_merge_file",
                        {"path": str(yaml_target), "value": {"meta": {"status": "ok"}}},
                    ),
                ]
                for name, args in calls:
                    result = await client.call_tool(name, args)
                    payload = json.loads("\n".join(item.text for item in result.content if hasattr(item, "text")))
                    assert payload["ok"] is True

        asyncio.run(_valid_ops())

        json_before_negative = json_target.read_text(encoding="utf-8")
        yaml_before_negative = yaml_target.read_text(encoding="utf-8")

        async def _invalid_ops() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "json_move_file",
                    {"path": str(json_target), "from_path": "/root/items/99/id", "to_path": "/meta/fail"},
                )

        async def _invalid_ops_yaml() -> None:
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer secret"},
                )
            ) as client:
                await client.call_tool(
                    "yaml_move_file",
                    {"path": str(yaml_target), "from_path": "/root/items/99/id", "to_path": "/meta/fail"},
                )

        with pytest.raises(Exception):
            asyncio.run(_invalid_ops())
        with pytest.raises(Exception):
            asyncio.run(_invalid_ops_yaml())

        assert json_target.read_text(encoding="utf-8") == json_before_negative
        assert yaml_target.read_text(encoding="utf-8") == yaml_before_negative

    final_json = json.loads(json_target.read_text(encoding="utf-8"))
    final_yaml = yaml.safe_load(yaml_target.read_text(encoding="utf-8"))
    assert final_json["meta"]["first_id"] == 1
    assert final_json["meta"]["status"] == "ok"
    assert final_json["root"]["items"][0]["second_id"] == 2
    assert "id" not in final_json["root"]["items"][1]
    assert final_yaml["meta"]["first_id"] == 1
    assert final_yaml["meta"]["status"] == "ok"
    assert final_yaml["root"]["items"][0]["second_id"] == 2
    assert "id" not in final_yaml["root"]["items"][1]
