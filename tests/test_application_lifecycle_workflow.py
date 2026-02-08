from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.http_integration_helpers import pick_free_port, wait_for_health, write_server_config


def _run_cli(repo_root: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "file_mcp_server", *args],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_operator_lifecycle_workflow(tmp_path: Path) -> None:
    port = pick_free_port()
    root_dir = tmp_path / "scope"
    root_dir.mkdir(parents=True, exist_ok=True)

    defaults_path, config_path, env_path, pidfile, _ = write_server_config(
        tmp_path,
        port=port,
        root_dir=root_dir,
    )
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
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
    assert start.returncode == 0, start.stderr or start.stdout
    assert "started (pid" in start.stdout

    try:
        status = _run_cli(repo_root, ["status", "--pidfile", str(pidfile)], env)
        assert status.returncode == 0
        assert "running (pid" in status.stdout

        health = wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=10.0)
        assert health["status"] == "ok"
    finally:
        stop = _run_cli(repo_root, ["stop", "--pidfile", str(pidfile), "--send-signal"], env)
        assert stop.returncode == 0, stop.stderr or stop.stdout

    final = _run_cli(repo_root, ["status", "--pidfile", str(pidfile)], env)
    assert final.returncode == 0
    assert "not running" in final.stdout
