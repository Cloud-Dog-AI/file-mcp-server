# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root


def _json_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("Authorization", f"Bearer {token}")
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=5.0) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


@pytest.mark.AT
@pytest.mark.api
@pytest.mark.req("FR-012")
@pytest.mark.req("FR-016")
@pytest.mark.req("FR-027")
def test_application_rest_file_lifecycle_base64_roundtrip(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _audit_log = write_server_config(
        runtime_dir,
        port=port,
        root_dir=root_dir,
        api_keys=["rest-at-key"],
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
        base_url = f"http://127.0.0.1:{port}"
        target = root_dir / "application-rest.bin"
        raw = b"application-rest-binary\x00payload"

        upload_status, upload_payload = _json_request(
            method="POST",
            url=f"{base_url}/files/upload_base64",
            token="rest-at-key",
            payload={
                "path": str(target),
                "data": base64.b64encode(raw).decode("ascii"),
                "overwrite": True,
            },
        )
        assert upload_status == 201
        file_id = upload_payload["file"]["id"]

        download_status, download_payload = _json_request(
            method="GET",
            url=f"{base_url}/files/{file_id}/download",
            token="rest-at-key",
        )
        assert download_status == 200
        assert base64.b64decode(download_payload["data"]) == raw

        delete_status, delete_payload = _json_request(
            method="DELETE",
            url=f"{base_url}/files/{file_id}",
            token="rest-at-key",
        )
        assert delete_status == 200
        assert delete_payload["deleted"] is True
        assert not target.exists()


@pytest.mark.AT
@pytest.mark.a2a
@pytest.mark.req("FR-012")
@pytest.mark.req("FR-027")
@pytest.mark.req("FR-029")
def test_application_a2a_file_management_transfers_base64_file(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _audit_log = write_server_config(
        runtime_dir,
        port=port,
        root_dir=root_dir,
        api_keys=["a2a-file-key"],
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
        base_url = f"http://127.0.0.1:{port}"
        target = root_dir / "a2a-transfer.bin"
        raw = b"a2a-transfer\x00payload"

        upload_task = {
            "id": "a2a-upload",
            "skill_id": "file-management",
            "input": {
                "text": json.dumps(
                    {
                        "tool": "b64_decode_to_file",
                        "arguments": {
                            "path": str(target),
                            "data": base64.b64encode(raw).decode("ascii"),
                            "overwrite": True,
                        },
                    }
                )
            },
        }
        upload_status, upload_payload = _json_request(
            method="POST",
            url=f"{base_url}/a2a/tasks",
            token="a2a-file-key",
            payload=upload_task,
        )
        assert upload_status == 200
        assert upload_payload["status"] == "completed"

        download_task = {
            "id": "a2a-download",
            "skill_id": "file-management",
            "input": {
                "text": json.dumps(
                    {
                        "tool": "b64_encode_file",
                        "arguments": {"path": str(target)},
                    }
                )
            },
        }
        download_status, download_payload = _json_request(
            method="POST",
            url=f"{base_url}/a2a/tasks",
            token="a2a-file-key",
            payload=download_task,
        )
        assert download_status == 200
        result = json.loads(download_payload["output"]["text"])
        assert base64.b64decode(result["data"]) == raw
