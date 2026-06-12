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
from urllib.request import Request, urlopen

from tests.http_integration_helpers import (
import pytest
    pick_free_port,
    running_server,
    wait_for_health,
    write_server_config,
)
from tests.path_helpers import project_root


def _inject_static_a2a_key(*, defaults_path: Path, config_path: Path) -> None:
    marker = 'api_keys:\n        - "${FILE_MCP_API_KEY_1}"'
    replacement = marker + '\n        - "12345678"'
    for path in (defaults_path, config_path):
        content = path.read_text(encoding="utf-8")
        if marker not in content:
            raise AssertionError(f"Unable to update auth key contract in {path}")
        path.write_text(content.replace(marker, replacement, 1), encoding="utf-8")


def _read_env_value(env_path: Path, key: str) -> str:
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        candidate_key, candidate_value = line.split("=", 1)
        if candidate_key.strip() == key:
            return candidate_value.strip()
    raise AssertionError(f"Missing env key: {key}")
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_application_a2a_health_flow_uses_test_a2a_api_key(tmp_path: Path) -> None:
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
    a2a_key = _read_env_value(env_path, "TEST_A2A_API_KEY")
    repo_root = project_root(Path(__file__))
    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")
        req = Request(
            f"http://127.0.0.1:{port}/a2a/health",
            headers={"Authorization": f"Bearer {a2a_key}"},
            method="GET",
        )
        with urlopen(req, timeout=2.0) as response:
            assert int(response.status) == 200
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["status"] == "ok"
        assert payload["a2a"]["base_path"] == "/a2a"
