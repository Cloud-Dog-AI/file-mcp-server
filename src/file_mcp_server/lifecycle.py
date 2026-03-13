# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# """
# License: Apache 2.0
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

"""
file-mcp-server — file_mcp_server/lifecycle.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Server module for file mcp server lifecycle.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import os
import signal
import time


@dataclass(frozen=True)
class LifecycleStatus:
    running: bool
    pid: Optional[int]
    message: str


def _pid_is_running(pid: int) -> bool:
    """Handle pid is running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(pidfile: Path) -> Optional[int]:
    """Read pid."""
    if not pidfile.exists():
        return None
    content = pidfile.read_text(encoding="utf-8").strip()
    if not content:
        return None
    try:
        return int(content)
    except ValueError:
        return None


def write_pid(pidfile: Path, pid: int) -> None:
    """Write pid."""
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(pid), encoding="utf-8")


def status_pidfile(pidfile: Path) -> LifecycleStatus:
    """Execute status pidfile."""
    pid = read_pid(pidfile)
    if pid is None:
        return LifecycleStatus(False, None, "not running")
    if _pid_is_running(pid):
        return LifecycleStatus(True, pid, f"running (pid {pid})")
    return LifecycleStatus(False, pid, f"stale pidfile (pid {pid})")


def start_pidfile(
    pidfile: Path, *, pid: Optional[int] = None, force: bool = False
) -> LifecycleStatus:
    """Execute start pidfile."""
    status = status_pidfile(pidfile)
    if status.running and not force:
        return LifecycleStatus(True, status.pid, "already running")
    pid = pid or os.getpid()
    write_pid(pidfile, pid)
    return LifecycleStatus(True, pid, f"started (pid {pid})")


def stop_pidfile(
    pidfile: Path, *, send_signal: bool = False, timeout_s: float = 5.0
) -> LifecycleStatus:
    """Execute stop pidfile."""
    status = status_pidfile(pidfile)
    if status.pid is None:
        return LifecycleStatus(False, None, "not running")
    if status.running:
        if send_signal:
            try:
                os.kill(status.pid, signal.SIGTERM)
            except ProcessLookupError:
                pidfile.unlink(missing_ok=True)
                return LifecycleStatus(False, status.pid, "stopped")

            deadline = time.monotonic() + max(0.0, timeout_s)
            while time.monotonic() < deadline:
                if not _pid_is_running(status.pid):
                    pidfile.unlink(missing_ok=True)
                    return LifecycleStatus(False, status.pid, "stopped")
                time.sleep(0.1)
            return LifecycleStatus(True, status.pid, "signal sent; still running")
        else:
            return LifecycleStatus(True, status.pid, "running; no signal sent")
    pidfile.unlink(missing_ok=True)
    return LifecycleStatus(False, status.pid, "stopped")
