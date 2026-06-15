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

from tests.env_runtime import runtime_env

import subprocess
import sys
from pathlib import Path
from tests.path_helpers import project_root

from tests.http_integration_helpers import (
    pick_free_port,
    wait_for_health,
    write_server_config,
)
import pytest


def _run_cli(
    repo_root: Path, args: list[str], env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "file_mcp_server", *args],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-027")


def test_operator_lifecycle_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    repo_root = project_root(Path(__file__))
    env = {
        key: value
        for key, value in runtime_env.items()
        if not (key.startswith("FILE_MCP_") or key.startswith("CLOUD_DOG__"))
    }
    env["PYTHONPATH"] = "src"

    start = _run_cli(
        repo_root,
        [
            "start",
            "--profile",
            "default",
            "--env-path",
            str(env_path),
            "--config-path",
            str(config_path),
            "--defaults-path",
            str(defaults_path),
            "--pidfile",
            str(pidfile),
            "--force",
        ],
        env,
    )

    start_ok = False
    try:
        assert start.returncode == 0, start.stderr or start.stdout
        assert "started (pid" in start.stdout
        start_ok = True

        status = _run_cli(repo_root, ["status", "--pidfile", str(pidfile)], env)
        assert status.returncode == 0
        assert "running (pid" in status.stdout

        health = wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=10.0)
        assert health["status"] == "ok"
    finally:
        if pidfile.exists():
            stop = _run_cli(
                repo_root, ["stop", "--pidfile", str(pidfile), "--send-signal"], env
            )
            if start_ok:
                assert stop.returncode == 0, stop.stderr or stop.stdout

    if start_ok:
        final = _run_cli(repo_root, ["status", "--pidfile", str(pidfile)], env)
        assert final.returncode == 0
        assert "not running" in final.stdout
