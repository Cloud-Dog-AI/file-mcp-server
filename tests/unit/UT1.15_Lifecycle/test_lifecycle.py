from __future__ import annotations

from pathlib import Path

from file_mcp_server.lifecycle import (
    read_pid,
    start_pidfile,
    status_pidfile,
    stop_pidfile,
)


def test_pidfile_lifecycle(tmp_path: Path) -> None:
    pidfile = tmp_path / "server.pid"

    status = status_pidfile(pidfile)
    assert not status.running

    started = start_pidfile(pidfile, pid=1234)
    assert started.running
    assert read_pid(pidfile) == 1234

    stopped = stop_pidfile(pidfile, send_signal=True, timeout_s=0.01)
    assert not stopped.running
    assert read_pid(pidfile) is None


def test_stop_pidfile_without_pid(tmp_path: Path) -> None:
    pidfile = tmp_path / "missing.pid"
    status = stop_pidfile(pidfile)
    assert not status.running
