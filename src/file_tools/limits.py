"""Operational limits helpers.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Helpers for enforcing size and timeout limits.
Requirements: NF1.2, CS1.5
Tasks: T18
Architecture: 7.2 Performance
Tests: ST1.7, UT1.5
Recent Change History:
- 2026-02-05: Initial limits helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import os
import signal
import threading


class LimitError(RuntimeError):
    """Raised when an operational limit is exceeded."""


def exceeds_max_file_size(path: Path, max_mb: Optional[int]) -> bool:
    if max_mb is None:
        return False
    if max_mb <= 0:
        return False
    size_bytes = path.stat().st_size
    return size_bytes > max_mb * 1024 * 1024


def enforce_max_file_size(path: Path, max_mb: Optional[int]) -> None:
    if exceeds_max_file_size(path, max_mb):
        raise LimitError(f"File exceeds size limit ({max_mb} MB): {path}")


@contextmanager
def enforce_timeout(timeout_s: Optional[int]) -> Iterator[None]:
    if timeout_s is None or timeout_s <= 0:
        yield
        return
    if os.name != "posix":
        yield
        return
    if threading.current_thread() is not threading.main_thread():
        # signal-based timers are only valid on the main thread.
        yield
        return

    def _handle_timeout(
        signum: int, frame: object
    ) -> None:  # pragma: no cover - signal handler
        raise TimeoutError("Operation timed out")

    previous = signal.signal(signal.SIGALRM, _handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
