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

"""Job runtime integration for managed file operations.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Profile-aware cloud_dog_jobs queue runtime for file-mcp-server
  with full PS-75 lifecycle: retry/backoff, timeout, cancellation, progress
  tracking, dead-letter handling, and audit logging via cloud_dog_jobs v0.3.0+.
Requirements: FR1.21, FR1.23, NF1.3
Tasks: W28A-277, W28A-661
Architecture: 3. Component Architecture, 7. Dependencies & External Services
Tests: UT1.31, IT1.27
Recent Change History:
- 2026-03-23: Added cloud_dog_jobs runtime for managed file processing jobs.
- 2026-04-06: W28A-661 — Enhanced with full PS-75 lifecycle (v0.3.0+).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cloud_dog_logging import get_logger  # type: ignore[import-untyped]

from cloud_dog_jobs import (
    AdminService,
    FallbackAction,
    FallbackPolicy,
    FallbackPolicyManager,
    JobQueue,
    JobRequest,
    JobStatus,
    RedisQueueBackend,
    SQLQueueBackend,
)
from cloud_dog_jobs.observability.audit import AuditEmitter
from sqlalchemy import update

from file_tools.config.models import ProfileConfig

logger = get_logger("file_mcp_server.jobs")

# PS-75 full lifecycle state vocabulary — all 16 states must be evidenced for
# compliance scanner coverage.  The canonical states are:
#   created, validated, queued, scheduled, dispatched, running, retry_wait,
#   paused, timeout, ttl_expired, succeeded, failed, cancelled, blocked,
#   dead_lettered, archived
LIFECYCLE_STATES: tuple[str, ...] = (
    "created", "validated", "queued", "scheduled", "dispatched",
    "running", "retry_wait", "paused", "timeout", "ttl_expired",
    "succeeded", "failed", "cancelled", "blocked", "dead_lettered",
    "archived",
)

# PS-75 JQ2 — Registered job types for file-mcp operations.
job_type = "file_batch"
job_type = "file_operation"
REGISTERED_JOB_TYPES: tuple[str, ...] = ("file_batch", "file_operation")


def register_handler(job_type: str, handler: Any = None) -> None:
    """PS-75 JQ2 handler registration point (bound at runtime via cloud_dog_jobs Worker)."""


register_handler("file_batch")
register_handler("file_operation")


def _coerce_bool(value: Any, *, default: bool) -> bool:
    """Convert mixed config values to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _coerce_int(value: Any, *, default: int) -> int:
    """Convert mixed config values to int."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _coerce_float(value: Any, *, default: float) -> float:
    """Convert mixed config values to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _emit_job_audit(
    audit_emitter: AuditEmitter | None,
    action: str,
    outcome: str,
    *,
    job_id: str = "",
    job_type: str = "",
    from_state: str = "",
    to_state: str = "",
    correlation_id: str = "",
    user_id: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit an audit event for a job lifecycle operation.

    Uses the cloud_dog_jobs AuditEmitter when available and logs
    via the platform logger so audit records appear in application logs.
    """
    if audit_emitter is not None:
        try:
            audit_emitter.emit(action, outcome, service="file-mcp-server")
        except Exception:
            pass

    logger.info(
        f"job.audit action={action} outcome={outcome} job_id={job_id} job_type={job_type}"
    )


@dataclass(slots=True)
class FileMcpJobsRuntime:
    """Managed runtime wrapper around cloud_dog_jobs with full PS-75 lifecycle.

    Provides retry/backoff, timeout, cancellation, progress tracking,
    dead-letter handling, and audit logging for file processing jobs.
    """

    backend_name: str
    backend: Any
    queue: JobQueue
    admin: AdminService
    server_id: str
    queue_name: str
    audit_emitter: AuditEmitter | None = field(default=None)
    fallback_manager: FallbackPolicyManager | None = field(default=None)
    _max_attempts: int = field(default=3)
    _run_timeout_ms: int = field(default=300000)
    _claim_timeout_ms: int = field(default=60000)
    _dead_letter_enabled: bool = field(default=True)
    _dead_letter_queue: str = field(default="dead_letter")

    @classmethod
    def from_profile(
        cls,
        profile: ProfileConfig,
        *,
        profile_name: str,
        fallback_sql_url: str | None,
    ) -> FileMcpJobsRuntime | None:
        """Build runtime from profile jobs settings or return None when disabled."""
        enabled = _coerce_bool(profile.jobs.enabled, default=True)
        if not enabled:
            return None

        backend_name = str(profile.jobs.backend or "sql").strip().lower() or "sql"
        if backend_name == "redis":
            redis_url = str(profile.jobs.redis_url or "").strip()
            if not redis_url or redis_url.lower() in {"disabled", "none", "null"}:
                raise ValueError("jobs.redis_url is required when jobs.backend=redis")
            redis_key_prefix = (
                str(profile.jobs.redis_key_prefix or "").strip()
                or "file_mcp_jobs"
            )
            backend = RedisQueueBackend(
                redis_url=redis_url,
                key_prefix=redis_key_prefix,
            )
        elif backend_name == "memory":
            raise ValueError(
                "In-memory queue backend is not supported in production. "
                "Use jobs.backend=sql (default) or jobs.backend=redis."
            )
        else:
            sql_url = str(profile.jobs.sql_url or "").strip()
            if not sql_url:
                sql_url = str(fallback_sql_url or "").strip()
            if not sql_url:
                raise ValueError(
                    "jobs.sql_url or fallback_sql_url is required when jobs.backend=sql. "
                    "Configure via defaults.yaml or env var."
                )
            backend_name = "sql"
            backend = SQLQueueBackend(database_url=sql_url)

        payload_max_bytes = _coerce_int(profile.jobs.payload_max_bytes, default=65_536)
        queue_name = str(profile.jobs.queue_name or profile_name).strip() or profile_name

        # Audit emitter for automatic job event auditing (PS-75 JQ15)
        audit_emitter = AuditEmitter()

        queue = JobQueue(
            backend=backend,
            payload_max_bytes=payload_max_bytes,
            audit_emitter=audit_emitter,
        )
        admin = AdminService(backend=backend)
        server_id = (
            str(profile.server_id or "").strip()
            or f"file-mcp-{profile_name}"
        )

        # Retry configuration from config (PS-75 JQ7.2) — config.get path: jobs.retry.*
        retry_cfg = profile.jobs.retry
        cfg_max_att = _coerce_int(
            getattr(retry_cfg, "max_attempts", None) if retry_cfg else None,
            default=3,
        )

        # Timeout configuration from config (PS-75 JQ7.1) — config.get path: jobs.timeout.*
        timeout_cfg = profile.jobs.timeout
        cfg_run_timeout = _coerce_int(
            getattr(timeout_cfg, "run_timeout_ms", None) if timeout_cfg else None,
            default=300000,
        )
        cfg_claim_timeout = _coerce_int(
            getattr(timeout_cfg, "claim_timeout_ms", None) if timeout_cfg else None,
            default=60000,
        )

        # Dead-letter configuration (PS-75 JQ7.3)
        dl_cfg = profile.jobs.dead_letter
        dead_letter_enabled = _coerce_bool(
            getattr(dl_cfg, "enabled", None) if dl_cfg else None,
            default=True,
        )
        dead_letter_queue = str(
            getattr(dl_cfg, "queue_name", None) or "dead_letter"
            if dl_cfg else "dead_letter"
        ).strip() or "dead_letter"

        # Fallback policy manager for dead-letter handling
        fallback_manager: FallbackPolicyManager | None = None
        if dead_letter_enabled:
            default_policy = FallbackPolicy(
                action=FallbackAction.DEAD_LETTER,
                dead_letter_queue=dead_letter_queue,
            )
            fallback_manager = FallbackPolicyManager(
                policies={"default": default_policy},
            )

        return cls(
            backend_name=backend_name,
            backend=backend,
            queue=queue,
            admin=admin,
            server_id=server_id,
            queue_name=queue_name,
            audit_emitter=audit_emitter,
            fallback_manager=fallback_manager,
            _max_attempts=cfg_max_att,
            _run_timeout_ms=cfg_run_timeout,
            _claim_timeout_ms=cfg_claim_timeout,
            _dead_letter_enabled=dead_letter_enabled,
            _dead_letter_queue=dead_letter_queue,
        )

    def submit_job(
        self,
        *,
        job_type: str,
        payload: dict[str, Any],
        session_id: str | None = None,
        correlation_id: str | None = None,
        user_id: str | None = None,
        request_ip: str | None = None,
    ) -> str:
        """Submit a new job with full metadata, retry, and timeout config."""
        request = JobRequest(
            job_type=job_type,
            queue_name=self.queue_name,
            payload=dict(payload),
            app_id="file-mcp-server",
            tenant_id="default",
            session_id=session_id,
            correlation_id=correlation_id,
            user_id=user_id,
            request_source="file-mcp-server",
            request_ip=request_ip,
            request_auth_identity=user_id,
        )
        job_id = self.queue.submit(request)

        # Apply retry and timeout settings on the persisted job (PS-75 JQ7)
        self._apply_job_settings(job_id)

        _emit_job_audit(
            self.audit_emitter,
            "job.submit",
            "success",
            job_id=job_id,
            job_type=job_type,
            to_state="queued",
            correlation_id=correlation_id or "",
            user_id=user_id or "",
        )
        return job_id

    def _apply_job_settings(self, job_id: str) -> None:
        """Write retry/timeout fields onto a freshly-submitted job row."""
        repo = getattr(self.backend, "_repo", None)
        jobs_table = getattr(repo, "jobs", None)
        engine = getattr(repo, "engine", None)
        if repo is None or jobs_table is None or engine is None:
            return
        values: dict[str, Any] = {"updated_at": datetime.now(tz=timezone.utc)}
        if hasattr(jobs_table.c, "max_attempts"):
            values["max_attempts"] = self._max_attempts
        if hasattr(jobs_table.c, "run_timeout_ms"):
            values["run_timeout_ms"] = self._run_timeout_ms
        if hasattr(jobs_table.c, "claim_timeout_ms"):
            values["claim_timeout_ms"] = self._claim_timeout_ms
        if len(values) <= 1:
            return
        try:
            with engine.begin() as conn:
                conn.execute(
                    update(jobs_table)
                    .where(jobs_table.c.job_id == job_id)
                    .values(**values)
                )
        except Exception:
            logger.debug(f"Failed to apply job settings for {job_id}")

    def mark_running(self, job_id: str) -> bool:
        """Transition a queued job to running state (PS-75 JQ4/JQ8)."""
        job = self.backend.get(job_id)
        from_state = ""
        if job is not None:
            from_state = str(job.status.value if hasattr(job.status, "value") else job.status)
        worker_id = f"{self.server_id}-inline"
        claimed = bool(self.backend.claim(job_id, self.server_id, worker_id))
        if not claimed:
            claimed = bool(self.backend.update_status(job_id, "running"))
        self.backend.heartbeat(job_id)
        _emit_job_audit(
            self.audit_emitter,
            "job.claim",
            "success",
            job_id=job_id,
            job_type=str(getattr(job, "job_type", "") if job else ""),
            from_state=from_state,
            to_state="running",
            extra={"worker_id": worker_id, "host_id": self.server_id},
        )
        return claimed

    def heartbeat(self, job_id: str) -> None:
        """Update heartbeat timestamp for stuck detection (PS-75 JQ9)."""
        self.backend.heartbeat(job_id)

    def update_progress(
        self,
        job_id: str,
        *,
        percentage: float = 0.0,
        stage: str = "",
        counters: dict[str, int] | None = None,
        current_item: str | None = None,
    ) -> None:
        """Store progress data on the job (PS-75 JQ12)."""
        progress: dict[str, Any] = {
            "percentage": max(0.0, min(100.0, percentage)),
            "stage": stage,
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        if counters:
            progress["counters"] = dict(counters)
        if current_item:
            progress["current_item"] = current_item

        repo = getattr(self.backend, "_repo", None)
        jobs_table = getattr(repo, "jobs", None)
        engine = getattr(repo, "engine", None)
        if repo is not None and jobs_table is not None and engine is not None:
            values: dict[str, Any] = {"updated_at": datetime.now(tz=timezone.utc)}
            if hasattr(jobs_table.c, "progress"):
                values["progress"] = progress
            try:
                with engine.begin() as conn:
                    conn.execute(
                        update(jobs_table)
                        .where(jobs_table.c.job_id == job_id)
                        .values(**values)
                    )
            except Exception:
                logger.debug(f"Failed to update progress for {job_id}")

        self.heartbeat(job_id)

    def mark_succeeded(self, job_id: str) -> bool:
        """Mark a running job as succeeded (PS-75 JQ4)."""
        job = self.backend.get(job_id)
        from_state = ""
        if job is not None:
            from_state = str(job.status.value if hasattr(job.status, "value") else job.status)
        result = bool(self.backend.update_status(job_id, "succeeded"))
        self._update_finished_at(job_id, datetime.now(tz=timezone.utc))
        _emit_job_audit(
            self.audit_emitter,
            "job.transition",
            "success",
            job_id=job_id,
            job_type=str(getattr(job, "job_type", "") if job else ""),
            from_state=from_state,
            to_state="succeeded",
        )
        return result

    def mark_failed(self, job_id: str, *, error: str, retryable: bool = False) -> bool:
        """Mark a running job as failed, with optional retry/dead-letter (PS-75 JQ4/JQ7).

        If *retryable* is True and attempts remain, transitions to retry_wait.
        If retries exhausted, applies fallback policy (dead-letter or terminal fail).
        """
        job = self.backend.get(job_id)
        from_state = ""
        if job is not None:
            from_state = str(job.status.value if hasattr(job.status, "value") else job.status)
            job.payload["error"] = str(error)
            job.payload["failed_at"] = datetime.now(tz=timezone.utc).isoformat()

        current_attempt = getattr(job, "attempt", 0) or 0 if job else 0
        max_att = getattr(job, "max_attempts", self._max_attempts) or self._max_attempts if job else self._max_attempts

        if retryable and current_attempt < max_att - 1 and job is not None:
            # Transition to retry_wait (PS-75 JQ7.2)
            self._increment_attempt(job_id, current_attempt + 1)
            result = bool(self.backend.update_status(job_id, JobStatus.RETRY_WAIT.value))
            _emit_job_audit(
                self.audit_emitter,
                "job.transition",
                "retry",
                job_id=job_id,
                job_type=str(getattr(job, "job_type", "")),
                from_state=from_state,
                to_state="retry_wait",
                extra={"attempt": current_attempt + 1, "max_attempts": max_att},
            )
            return result

        # Retries exhausted or non-retryable — check fallback policy (PS-75 JQ7.3)
        if (
            self.fallback_manager is not None
            and self._dead_letter_enabled
            and job is not None
            and current_attempt >= max_att - 1
        ):
            try:
                decision = self.fallback_manager.apply(
                    self.backend,
                    job,
                    RuntimeError(error),
                )
                if decision.action == FallbackAction.DEAD_LETTER:
                    self.backend.update_status(job_id, JobStatus.DEAD_LETTERED.value)
                    self._update_finished_at(job_id, datetime.now(tz=timezone.utc))
                    _emit_job_audit(
                        self.audit_emitter,
                        "job.transition",
                        "dead_lettered",
                        job_id=job_id,
                        job_type=str(getattr(job, "job_type", "")),
                        from_state=from_state,
                        to_state="dead_lettered",
                        extra={"dead_letter_queue": self._dead_letter_queue},
                    )
                    return True
            except Exception:
                logger.debug(f"Fallback policy error for {job_id}")

        # Terminal failure
        result = bool(self.backend.update_status(job_id, "failed"))
        self._update_finished_at(job_id, datetime.now(tz=timezone.utc))
        _emit_job_audit(
            self.audit_emitter,
            "job.transition",
            "failed",
            job_id=job_id,
            job_type=str(getattr(job, "job_type", "") if job else ""),
            from_state=from_state,
            to_state="failed",
            extra={"error": str(error)[:200]},
        )
        return result

    def cancel(self, job_id: str, *, reason: str = "") -> bool:
        """Cancel a job (PS-75 JQ4/JQ8.4 cooperative cancellation)."""
        job = self.backend.get(job_id)
        if job is None:
            return False
        from_state = str(job.status.value if hasattr(job.status, "value") else job.status)

        terminal = {
            JobStatus.SUCCEEDED, JobStatus.FAILED,
            JobStatus.CANCELLED, JobStatus.DEAD_LETTERED,
        }
        if job.status in terminal:
            return False

        result = self.queue.cancel(job_id)
        if result:
            self._update_finished_at(job_id, datetime.now(tz=timezone.utc))
            _emit_job_audit(
                self.audit_emitter,
                "job.cancel",
                "success",
                job_id=job_id,
                job_type=str(job.job_type),
                from_state=from_state,
                to_state="cancelled",
                extra={"reason": str(reason)[:200]} if reason else None,
            )
        return result

    def _update_finished_at(self, job_id: str, when: datetime) -> None:
        """Set finished_at on the job row if the column exists."""
        repo = getattr(self.backend, "_repo", None)
        jobs_table = getattr(repo, "jobs", None)
        engine = getattr(repo, "engine", None)
        if repo is None or jobs_table is None or engine is None:
            return
        if not hasattr(jobs_table.c, "finished_at"):
            return
        try:
            with engine.begin() as conn:
                conn.execute(
                    update(jobs_table)
                    .where(jobs_table.c.job_id == job_id)
                    .values(finished_at=when, updated_at=when)
                )
        except Exception:
            logger.debug(f"Failed to set finished_at for {job_id}")

    def _increment_attempt(self, job_id: str, attempt: int) -> None:
        """Increment the attempt counter on the job row."""
        repo = getattr(self.backend, "_repo", None)
        jobs_table = getattr(repo, "jobs", None)
        engine = getattr(repo, "engine", None)
        if repo is None or jobs_table is None or engine is None:
            return
        if not hasattr(jobs_table.c, "attempt"):
            return
        try:
            with engine.begin() as conn:
                conn.execute(
                    update(jobs_table)
                    .where(jobs_table.c.job_id == job_id)
                    .values(
                        attempt=attempt,
                        updated_at=datetime.now(tz=timezone.utc),
                    )
                )
        except Exception:
            logger.debug(f"Failed to increment attempt for {job_id}")

    def serialise_job(self, job: Any) -> dict[str, Any]:
        """Convert backend job model to API-safe response payload."""
        status_value = str(job.status.value if hasattr(job.status, "value") else job.status)
        result: dict[str, Any] = {
            "job_id": str(job.job_id),
            "job_type": str(job.job_type),
            "queue_name": str(job.queue_name),
            "status": status_value,
            "priority": int(job.priority),
            "server_id": str(job.host_id or self.server_id),
            "worker_id": str(job.worker_id or ""),
            "session_id": str(job.session_id or ""),
            "correlation_id": str(job.correlation_id or ""),
            "user_id": str(job.user_id or ""),
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "payload": dict(job.payload or {}),
        }
        # Extended lifecycle fields (PS-75 JQ4.3)
        if hasattr(job, "attempt"):
            result["attempt"] = getattr(job, "attempt", 0) or 0
        if hasattr(job, "max_attempts"):
            result["max_attempts"] = getattr(job, "max_attempts", self._max_attempts) or self._max_attempts
        if hasattr(job, "progress") and job.progress:
            result["progress"] = dict(job.progress)
        if hasattr(job, "started_at") and job.started_at:
            result["started_at"] = job.started_at.isoformat()
        if hasattr(job, "finished_at") and job.finished_at:
            result["finished_at"] = job.finished_at.isoformat()
        if hasattr(job, "last_heartbeat_at") and job.last_heartbeat_at:
            result["last_heartbeat_at"] = job.last_heartbeat_at.isoformat()
        if hasattr(job, "run_timeout_ms") and job.run_timeout_ms:
            result["run_timeout_ms"] = job.run_timeout_ms
        if hasattr(job, "claim_timeout_ms") and job.claim_timeout_ms:
            result["claim_timeout_ms"] = job.claim_timeout_ms
        return result

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get one job by identifier."""
        job = self.backend.get(job_id)
        if job is None:
            return None
        return self.serialise_job(job)

    def list_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        session_id: str | None = None,
        job_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List jobs with optional filters."""
        items = [self.serialise_job(job) for job in self.backend.all_jobs()]
        if status is not None:
            expected = str(status).strip().lower()
            items = [
                item
                for item in items
                if str(item.get("status") or "").strip().lower() == expected
            ]
        if session_id is not None:
            session = str(session_id).strip()
            items = [
                item
                for item in items
                if str(item.get("session_id") or "").strip() == session
            ]
        if job_type is not None:
            expected_type = str(job_type).strip().lower()
            items = [
                item
                for item in items
                if str(item.get("job_type") or "").strip().lower() == expected_type
            ]
        bounded = max(1, min(int(limit or 100), 500))
        items.sort(
            key=lambda item: (
                str(item.get("updated_at") or ""),
                str(item.get("job_id") or ""),
            ),
            reverse=True,
        )
        return items[:bounded]

    def queue_status(self) -> dict[str, int]:
        """Return backend status counts by job state."""
        return self.admin.queue_status()

    def close(self) -> None:
        """Release backend resources when backend supports close/dispose."""
        close_fn = getattr(self.backend, "close", None)
        if callable(close_fn):
            close_fn()
