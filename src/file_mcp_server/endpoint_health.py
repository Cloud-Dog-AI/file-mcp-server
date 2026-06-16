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

"""Endpoint health checks and retry policy for storage backends.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Startup and runtime endpoint health state machine with retry limits.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import socket
import threading
import time
from typing import Any, Protocol

from cloud_dog_storage import path_utils

from file_tools.adapters import ConnectionError, HTTPError, Timeout

from file_tools.config.models import EndpointHealthConfig, ProfileConfig
from file_tools.storage import StorageBackend, build_storage_backend


@dataclass
class EndpointState:
    backend: str
    status: str
    reason: str
    last_error: str
    updated_at: str
    failures_in_window: int
    consecutive_failures: int
    retries_used: int
    requires_restart: bool


class LogLike(Protocol):
    """Protocol for structured logger methods used by health checks."""

    def info(self, msg: str, **extra: Any) -> None: ...

    def warning(self, msg: str, **extra: Any) -> None: ...


class EndpointHealthManager:
    def __init__(self) -> None:
        """Initialise the instance state."""
        self._states: dict[str, dict[str, EndpointState]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._failure_times: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _set_state(self, profile_name: str, state: EndpointState) -> None:
        """Handle set state."""
        with self._lock:
            self._states[profile_name][state.backend] = state

    def get_profile_states(self, profile_name: str) -> dict[str, EndpointState]:
        """Return profile states."""
        with self._lock:
            return dict(self._states.get(profile_name, {}))

    def get_state(self, profile_name: str, backend: str) -> EndpointState | None:
        """Return state."""
        with self._lock:
            return self._states.get(profile_name, {}).get(backend)

    def classify_exception(self, exc: Exception) -> str:
        """Execute classify exception."""
        if isinstance(exc, TimeoutError):
            return "temporary_unavailable"
        if isinstance(exc, socket.timeout):
            return "temporary_unavailable"
        if isinstance(exc, Timeout):
            return "temporary_unavailable"
        if isinstance(exc, ConnectionError):
            return "temporary_unavailable"
        if isinstance(exc, HTTPError):
            status = exc.response.status_code if exc.response is not None else None
            if status in {401, 403}:
                return "auth_failed"
            if status in {408, 409, 423, 425, 429, 500, 502, 503, 504}:
                return "busy_temporary"
            return "failed"
        text = str(exc).lower()
        if "timed out" in text or "timeout" in text:
            return "temporary_unavailable"
        if (
            "uthoriz" in text
            or "uthoris" in text
            or "forbidden" in text
            or "invalid_grant" in text
            or "expired or revoked" in text
            or ("refresh token" in text and "revoked" in text)
        ):
            return "auth_failed"
        if "temporar" in text or "busy" in text or "too many requests" in text:
            return "busy_temporary"
        return "failed"

    def _probe_backend(self, backend: StorageBackend, profile: ProfileConfig) -> None:
        """Handle probe backend."""
        if backend.backend_name == "local":
            for root in profile.scope.roots:
                path_utils.resolve_strict(root)
            return
        # For remote/object endpoints, a lightweight directory listing/stat is enough
        # to verify connectivity/auth without mutating data.
        backend.list_dir("/", recursive=False)

    def _configured_backends(self, profile: ProfileConfig) -> list[str]:
        """Handle configured backends."""

        def _configured(value: str | None) -> bool:
            """Handle configured."""
            if value is None:
                return False
            cleaned = value.strip()
            return bool(cleaned) and "${" not in cleaned

        backends = {(profile.storage.backend or "local").strip().lower() or "local"}
        if _configured(profile.storage.s3.endpoint):
            backends.add("s3")
        if _configured(profile.storage.webdav.base_url):
            backends.add("webdav")
        if _configured(profile.storage.ftp.host):
            backends.add("ftp")
        if _configured(profile.storage.google_drive.folder_id) or _configured(
            profile.storage.google_drive.folder_url
        ):
            backends.add("google_drive")
        return sorted(backends)

    def _health_cfg(self, profile: ProfileConfig) -> EndpointHealthConfig:
        """Handle health cfg."""
        return profile.endpoint_health

    def _int_or(self, value: Any, default: int) -> int:
        """Handle int or."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return default
        return default

    def _bool_or(self, value: Any, default: bool) -> bool:
        """Handle bool or."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return default

    def _now(self) -> tuple[float, str]:
        """Handle now."""
        now = time.time()
        return now, datetime.now(timezone.utc).isoformat()

    def run_startup_checks(
        self,
        *,
        profile_name: str,
        profile: ProfileConfig,
        logger: LogLike | None,
    ) -> None:
        """Execute run startup checks."""
        cfg = self._health_cfg(profile)
        if not self._bool_or(cfg.enabled, True):
            return
        if not self._bool_or(cfg.check_on_startup, True):
            return

        check_all = self._bool_or(cfg.check_all_configured_backends, True)
        backends = (
            self._configured_backends(profile)
            if check_all
            else [(profile.storage.backend or "local").strip().lower() or "local"]
        )
        max_retries = self._int_or(cfg.max_retries, 3)
        retry_interval_s = self._int_or(cfg.retry_interval_s, 2)
        retry_window_s = self._int_or(cfg.retry_window_s, 30)
        max_failures_before_restart = self._int_or(cfg.max_failures_before_restart, 5)

        for backend_name in backends:
            # Clone profile in-memory with target backend.
            profile_for_backend = profile.model_copy(deep=True)
            profile_for_backend.storage.backend = backend_name
            attempts = 0
            retries_used = 0
            last_error = ""
            status = "unknown"
            reason = "not_checked"
            while attempts <= max_retries:
                attempts += 1
                try:
                    backend = build_storage_backend(profile_for_backend)
                    self._probe_backend(backend, profile_for_backend)
                    status = "healthy"
                    reason = "startup_probe_ok"
                    last_error = ""
                    break
                except Exception as exc:  # pragma: no cover - network dependent
                    category = self.classify_exception(exc)
                    status = category
                    reason = "startup_probe_failed"
                    last_error = str(exc)
                    now, _ = self._now()
                    key = (profile_name, backend_name)
                    dq = self._failure_times[key]
                    dq.append(now)
                    while dq and now - dq[0] > retry_window_s:
                        dq.popleft()
                    failures_in_window = len(dq)
                    if logger:
                        logger.warning(
                            "endpoint-check",
                            backend=backend_name,
                            attempt=attempts,
                            max_attempts=max_retries + 1,
                            status=category,
                            error=str(exc),
                        )
                    can_retry = (
                        category in {"temporary_unavailable", "busy_temporary"}
                        and attempts <= max_retries
                    )
                    if can_retry:
                        retries_used += 1
                        time.sleep(retry_interval_s)
                        continue
                    break

            now, iso_now = self._now()
            key = (profile_name, backend_name)
            dq = self._failure_times[key]
            while dq and now - dq[0] > retry_window_s:
                dq.popleft()
            failures_in_window = len(dq)
            prev = self.get_state(profile_name, backend_name)
            consecutive_failures = (
                0
                if status == "healthy"
                else ((prev.consecutive_failures + 1) if prev else 1)
            )
            requires_restart = consecutive_failures >= max_failures_before_restart
            state = EndpointState(
                backend=backend_name,
                status=status,
                reason=reason,
                last_error=last_error,
                updated_at=iso_now,
                failures_in_window=failures_in_window,
                consecutive_failures=consecutive_failures,
                retries_used=retries_used,
                requires_restart=requires_restart,
            )
            self._set_state(profile_name, state)
            if logger:
                logger.info(
                    "endpoint-startup-status",
                    backend=backend_name,
                    status=state.status,
                    retries_used=state.retries_used,
                    failures_in_window=state.failures_in_window,
                    requires_restart=state.requires_restart,
                )

    def maybe_recover_backend(
        self,
        *,
        profile_name: str,
        profile: ProfileConfig,
        backend_name: str,
        logger: LogLike | None,
    ) -> EndpointState | None:
        """Execute maybe recover backend."""
        cfg = self._health_cfg(profile)
        if not self._bool_or(cfg.enabled, True):
            return None
        state = self.get_state(profile_name, backend_name)
        if state is None or state.status == "healthy":
            return state
        recover_after_s = self._int_or(cfg.recover_after_s, 30)
        now = datetime.now(timezone.utc)
        try:
            then = datetime.fromisoformat(state.updated_at)
        except ValueError:
            then = now
        if (now - then).total_seconds() < recover_after_s:
            return state

        profile_for_backend = profile.model_copy(deep=True)
        profile_for_backend.storage.backend = backend_name
        if logger:
            logger.info(
                "endpoint-recover-attempt",
                backend=backend_name,
                previous_status=state.status,
            )
        try:
            backend = build_storage_backend(profile_for_backend)
            self._probe_backend(backend, profile_for_backend)
            now_ts, iso_now = self._now()
            recovered = EndpointState(
                backend=backend_name,
                status="healthy",
                reason="recovered",
                last_error="",
                updated_at=iso_now,
                failures_in_window=0,
                consecutive_failures=0,
                retries_used=0,
                requires_restart=False,
            )
            self._set_state(profile_name, recovered)
            if logger:
                logger.info("endpoint-recover-success", backend=backend_name)
            return recovered
        except Exception as exc:  # pragma: no cover - network dependent
            category = self.classify_exception(exc)
            now_ts, iso_now = self._now()
            failed = EndpointState(
                backend=backend_name,
                status=category,
                reason="recover_failed",
                last_error=str(exc),
                updated_at=iso_now,
                failures_in_window=state.failures_in_window + 1,
                consecutive_failures=state.consecutive_failures + 1,
                retries_used=state.retries_used + 1,
                requires_restart=state.requires_restart,
            )
            self._set_state(profile_name, failed)
            if logger:
                logger.warning(
                    "endpoint-recover-failed",
                    backend=backend_name,
                    status=category,
                    error=str(exc),
                )
            return failed


ENDPOINT_HEALTH_MANAGER = EndpointHealthManager()
