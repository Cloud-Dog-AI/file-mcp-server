# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root


def _request(
    *,
    method: str,
    url: str,
    payload: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    body = b""
    request = Request(url, method=method)
    request.add_header("Accept", "application/json")
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request.data = body
        request.add_header("Content-Type", "application/json")
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=5.0) as response:
            response_body = response.read().decode("utf-8")
            return int(response.status), json.loads(response_body or "{}")
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        return int(exc.code), json.loads(response_body or "{}")


@pytest.mark.IT
@pytest.mark.api
@pytest.mark.req("FR-012")
@pytest.mark.req("FR-016")
@pytest.mark.req("FR-017")
@pytest.mark.req("FR-029")
def test_ps78_rest_file_lifecycle_uses_profile_scope_and_audit(
    tmp_path: Path,
) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, audit_log = write_server_config(
        runtime_dir,
        port=port,
        root_dir=root_dir,
        api_keys=["rest-key"],
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
        target = root_dir / "ps78-rest.txt"

        anon_status, anon_payload = _request(
            method="GET",
            url=f"{base_url}/files?{urlencode({'path': str(root_dir)})}",
        )
        assert anon_status == 401
        assert anon_payload["errors"][0]["code"] == "UNAUTHENTICATED"

        create_status, create_payload = _request(
            method="POST",
            url=f"{base_url}/files/upload",
            token="rest-key",
            payload={
                "path": str(target),
                "content": "rest lifecycle content",
                "overwrite": True,
            },
        )
        assert create_status == 201
        assert create_payload["ok"] is True
        file_id = create_payload["file"]["id"]
        assert create_payload["file"]["path"] == str(target)

        list_status, list_payload = _request(
            method="GET",
            url=f"{base_url}/files?{urlencode({'path': str(root_dir)})}",
            token="rest-key",
        )
        assert list_status == 200
        assert any(item["id"] == file_id for item in list_payload["items"])

        meta_status, meta_payload = _request(
            method="GET",
            url=f"{base_url}/files/{file_id}",
            token="rest-key",
        )
        assert meta_status == 200
        assert meta_payload["file"]["size"] == len(b"rest lifecycle content")

        download_status, download_payload = _request(
            method="GET",
            url=f"{base_url}/files/{file_id}/download",
            token="rest-key",
        )
        assert download_status == 200
        assert base64.b64decode(download_payload["data"]) == b"rest lifecycle content"

        delete_status, delete_payload = _request(
            method="DELETE",
            url=f"{base_url}/files/{file_id}",
            token="rest-key",
        )
        assert delete_status == 200
        assert delete_payload["deleted"] is True
        assert not target.exists()

        missing_status, missing_payload = _request(
            method="GET",
            url=f"{base_url}/files/{file_id}",
            token="rest-key",
        )
        assert missing_status == 404
        assert missing_payload["errors"][0]["code"] == "NOT_FOUND"

    audit_text = audit_log.read_text(encoding="utf-8")
    assert "write_file" in audit_text
    assert "delete_file" in audit_text


@pytest.mark.IT
@pytest.mark.api
@pytest.mark.req("CS-002")
@pytest.mark.req("CS-009")
@pytest.mark.req("FR-017")
def test_ps78_rest_file_lifecycle_rejects_read_only_scope(
    tmp_path: Path,
) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _audit_log = write_server_config(
        runtime_dir,
        port=port,
        root_dir=root_dir,
        api_keys=["bootstrap-key"],
        extra_env_lines=[
            "FILE_MCP_ADMIN_UI_ENABLED=true",
            "FILE_MCP_ADMIN_UI_TOKEN=admin-token",
        ],
    )

    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
        extra_env={
            "FILE_MCP_ADMIN_UI_ENABLED": "true",
            "FILE_MCP_ADMIN_UI_TOKEN": "admin-token",
        },
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")
        base_url = f"http://127.0.0.1:{port}"

        user_status, user_payload = _request(
            method="POST",
            url=f"{base_url}/admin/users",
            token=None,
            payload={"username": "rest-read-only", "display_name": "REST Read Only"},
        )
        assert user_status == 401

        request = Request(f"{base_url}/admin/users", method="POST")
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        request.add_header("x-admin-token", "admin-token")
        request.data = json.dumps(
            {"username": "rest-read-only", "display_name": "REST Read Only"}
        ).encode("utf-8")
        with urlopen(request, timeout=5.0) as response:
            admin_payload = json.loads(response.read().decode("utf-8"))
        user_id = str(admin_payload["user"]["id"])

        request = Request(f"{base_url}/admin/api-keys", method="POST")
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        request.add_header("x-admin-token", "admin-token")
        request.data = json.dumps(
            {
                "user_id": user_id,
                "label": "rest-read-only-key",
                "scopes": ["profile:default:read"],
            }
        ).encode("utf-8")
        with urlopen(request, timeout=5.0) as response:
            key_payload = json.loads(response.read().decode("utf-8"))
        read_only_key = str(key_payload["api_key"]["secret"])

        list_status, list_payload = _request(
            method="GET",
            url=f"{base_url}/files?{urlencode({'path': str(root_dir)})}",
            token=read_only_key,
        )
        assert list_status == 200
        assert list_payload["ok"] is True

        write_status, write_payload = _request(
            method="POST",
            url=f"{base_url}/files/upload",
            token=read_only_key,
            payload={
                "path": str(root_dir / "blocked.txt"),
                "content": "blocked",
                "overwrite": True,
            },
        )
        assert write_status == 403
        assert write_payload["errors"][0]["code"] == "FORBIDDEN"
