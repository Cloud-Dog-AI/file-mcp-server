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

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root
import pytest


def _inject_static_a2a_key(*, defaults_path: Path, config_path: Path) -> None:
    marker = 'api_keys:\n        - "${FILE_MCP_API_KEY_1}"'
    replacement = marker + '\n        - "12345678"'
    for path in (defaults_path, config_path):
        content = path.read_text(encoding="utf-8")
        if marker not in content:
            raise AssertionError(f"Unable to update auth key contract in {path}")
        path.write_text(content.replace(marker, replacement, 1), encoding="utf-8")


def _request_status(url: str, *, auth: str | None = None) -> tuple[int, dict]:
    headers = {}
    if auth:
        headers["Authorization"] = auth
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=2.0) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = {}
        body = exc.read().decode("utf-8", errors="replace").strip()
        if body:
            payload = json.loads(body)
        return int(exc.code), payload
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-029")


def test_a2a_health_auth_matrix_401_401_200(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
        extra_env_lines=["TEST_A2A_API_KEY=12345678"],
    )
    _inject_static_a2a_key(defaults_path=defaults_path, config_path=config_path)
    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")
        endpoint = f"http://127.0.0.1:{port}/a2a/health"

        no_auth_status, _ = _request_status(endpoint)
        wrong_auth_status, _ = _request_status(
            endpoint, auth="Authorization missing-scheme"
        )
        valid_auth_status, valid_payload = _request_status(
            endpoint, auth="Bearer 12345678"
        )

        assert no_auth_status == 401
        assert wrong_auth_status == 401
        assert valid_auth_status == 200
        assert valid_payload["status"] == "ok"
        assert valid_payload["service"] == "file-mcp-server"
