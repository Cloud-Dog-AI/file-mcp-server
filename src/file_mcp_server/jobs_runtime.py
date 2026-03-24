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
Description: Profile-aware cloud_dog_jobs queue runtime for file-mcp-server.
Requirements: FR1.21, FR1.23, NF1.3
Tasks: W28A-277
Architecture: 3. Component Architecture, 7. Dependencies & External Services
Tests: UT1.31, IT1.27
Recent Change History:
- 2026-03-23: Added cloud_dog_jobs runtime for managed file processing jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from datetime import datetime
from typing import Any

from cloud_dog_jobs import (
    AdminService,
    JobQueue,
    JobRequest,
    MemoryQueueBackend,
    RedisQueueBackend,
    SQLQueueBackend,
)

from file_tools.config.models import ProfileConfig


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


@dataclass(slots=True)
class FileMcpJobsRuntime:
    """Managed runtime wrapper around cloud_dog_jobs primitives."""

    backend_name: str
    backend: Any
    queue: JobQueue
    admin: AdminService
    server_id: str
    queue_name: str

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
            backend = MemoryQueueBackend()
        else:
            sql_url = str(profile.jobs.sql_url or "").strip()
            if not sql_url:
                sql_url = str(fallback_sql_url or "").strip()
            if not sql_url:
                sql_url = "sqlite:///database/file_mcp.db"
            backend_name = "sql"
            backend = SQLQueueBackend(database_url=sql_url)

        payload_max_bytes = _coerce_int(profile.jobs.payload_max_bytes, default=65_536)
        queue_name = str(profile.jobs.queue_name or profile_name).strip() or profile_name
        queue = JobQueue(backend=backend, payload_max_bytes=payload_max_bytes)
        admin = AdminService(backend=backend)
        server_id = (
            str(profile.server_id or "").strip()
            or f"file-mcp-{profile_name}"
        )
        return cls(
            backend_name=backend_name,
            backend=backend,
            queue=queue,
            admin=admin,
            server_id=server_id,
            queue_name=queue_name,
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
        """Submit a new job and return its identifier."""
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
        return self.queue.submit(request)

    def mark_running(self, job_id: str) -> bool:
        """Transition a queued job to running state."""
        worker_id = f"{self.server_id}-inline"
        claimed = bool(self.backend.claim(job_id, self.server_id, worker_id))
        if not claimed:
            claimed = bool(self.backend.update_status(job_id, "running"))
        self.backend.heartbeat(job_id)
        return claimed

    def mark_succeeded(self, job_id: str) -> bool:
        """Mark a job as succeeded."""
        return bool(self.backend.update_status(job_id, "succeeded"))

    def mark_failed(self, job_id: str, *, error: str) -> bool:
        """Mark a job as failed."""
        job = self.backend.get(job_id)
        if job is not None:
            job.payload["error"] = str(error)
            job.payload["failed_at"] = datetime.now(tz=timezone.utc).isoformat()
        return bool(self.backend.update_status(job_id, "failed"))

    def serialise_job(self, job: Any) -> dict[str, Any]:
        """Convert backend job model to API-safe response payload."""
        status_value = str(job.status.value if hasattr(job.status, "value") else job.status)
        return {
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
