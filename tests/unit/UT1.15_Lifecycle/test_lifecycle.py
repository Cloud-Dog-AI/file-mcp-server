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

from pathlib import Path

from file_mcp_server.lifecycle import (
    read_pid,
    start_pidfile,
    status_pidfile,
    stop_pidfile,
)
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


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
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_stop_pidfile_without_pid(tmp_path: Path) -> None:
    pidfile = tmp_path / "missing.pid"
    status = stop_pidfile(pidfile)
    assert not status.running
