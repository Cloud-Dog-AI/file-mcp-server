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

import contextvars
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional, TypeVar

import concurrent.futures
import os
import signal
import threading

_T = TypeVar("_T")


_operation_cancel_event: contextvars.ContextVar[threading.Event | None] = (
    contextvars.ContextVar("file_mcp_operation_cancel_event", default=None)
)


class LimitError(RuntimeError):
    """Raised when an operational limit is exceeded."""


def set_operation_cancel_event(
    event: threading.Event,
) -> contextvars.Token[threading.Event | None]:
    """Bind a cooperative cancellation event to the current tool execution."""
    return _operation_cancel_event.set(event)


def reset_operation_cancel_event(
    token: contextvars.Token[threading.Event | None],
) -> None:
    """Restore the prior tool-execution cancellation context."""
    _operation_cancel_event.reset(token)


def raise_if_operation_cancelled() -> None:
    """Raise a timeout when the async transport deadline has expired."""
    event = _operation_cancel_event.get()
    if event is not None and event.is_set():
        raise TimeoutError("Operation timed out")


def exceeds_max_file_size(path: Path, max_mb: Optional[int]) -> bool:
    """Execute exceeds max file size."""
    if max_mb is None:
        return False
    if max_mb <= 0:
        return False
    size_bytes = path.stat().st_size
    return size_bytes > max_mb * 1024 * 1024


def enforce_max_file_size(path: Path, max_mb: Optional[int]) -> None:
    """Execute enforce max file size."""
    if exceeds_max_file_size(path, max_mb):
        raise LimitError(f"File exceeds size limit ({max_mb} MB): {path}")


@contextmanager
def enforce_timeout(timeout_s: Optional[int]) -> Iterator[None]:
    """Execute enforce timeout."""
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
        """Handle handle timeout."""
        raise TimeoutError("Operation timed out")

    previous = signal.signal(signal.SIGALRM, _handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def call_with_timeout(func: Callable[[], _T], timeout_s: Optional[float]) -> _T:
    """Run ``func()`` under a wall-clock timeout that works on ANY thread.

    ``enforce_timeout`` relies on POSIX signals, which are only valid on the main
    thread; MCP tool calls are dispatched on anyio worker threads, so the signal
    timer silently no-ops there (W28R-3013: proven identical on deployed 3.12 and
    local 3.13). This helper enforces the timeout regardless of dispatch thread:

    - On the main POSIX thread it uses the precise signal timer (interrupts
      blocking syscalls in-place).
    - Otherwise it runs ``func`` in a single-worker executor and abandons it on
      timeout, raising :class:`TimeoutError` so the caller returns a timeout
      result instead of blocking for the full operation.

    Raises:
        TimeoutError: if ``func`` does not complete within ``timeout_s``.
    """
    if timeout_s is None or timeout_s <= 0:
        return func()
    if os.name == "posix" and threading.current_thread() is threading.main_thread():
        with enforce_timeout(int(timeout_s) if float(timeout_s).is_integer() else timeout_s):
            return func()
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="file-mcp-timeout"
    )
    # Preserve the cooperative cancellation context when an MCP worker thread
    # delegates the blocking operation to this timeout executor.
    context = contextvars.copy_context()
    future = executor.submit(context.run, func)
    try:
        return future.result(timeout=float(timeout_s))
    except concurrent.futures.TimeoutError as exc:  # pragma: no cover - timing
        cancel_event = _operation_cancel_event.get()
        if cancel_event is not None:
            cancel_event.set()
        raise TimeoutError("Operation timed out") from exc
    finally:
        # Do not block on an abandoned task (wait=False); the worker thread
        # unwinds on its own. Python 3.9+ cancels not-yet-started futures.
        executor.shutdown(wait=False, cancel_futures=True)
