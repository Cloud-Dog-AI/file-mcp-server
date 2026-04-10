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

"""Audit adapter backed by cloud_dog_logging.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Domain audit compatibility layer mapping file-tool events to PS-40 schema.
Requirements: FR1.3, FR1.5, FR1.8, CS1.1
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-19: Replaced bespoke audit writer with cloud_dog_logging-backed adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

from cloud_dog_storage import path_utils

from cloud_dog_logging.audit_logger import (  # type: ignore[import-untyped]
    AuditLogger as PlatformAuditLogger,
)
from cloud_dog_logging.audit_schema import (  # type: ignore[import-untyped]
    Actor,
    AuditEvent as PlatformAuditEvent,
    Target,
)
from cloud_dog_logging.correlation import get_correlation_id  # type: ignore[import-untyped]
from cloud_dog_logging.correlation import (  # type: ignore[import-untyped]
    set_environment,
    set_service_instance,
    set_service_name,
)
from cloud_dog_logging.presets import BUILTIN_PRESETS  # type: ignore[import-untyped]
from cloud_dog_logging.redaction import RedactionEngine  # type: ignore[import-untyped]
from cloud_dog_logging.sinks.base import AuditSink  # type: ignore[import-untyped]


@dataclass
class FileAuditEvent:
    """Legacy-compatible domain event shape for file-mcp audit emission."""

    tool: str
    action: str
    status: str
    outcome: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    profile: Optional[str] = None
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    duration_ms: Optional[float] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


def _to_outcome(value: str) -> str:
    """Handle to outcome."""
    normalized = (value or "").strip().lower()
    if normalized in {"success", "ok"}:
        return "success"
    if normalized in {"failure", "failed"}:
        return "failure"
    return "error"


def _to_legacy_status(outcome: str) -> str:
    """Handle to legacy status."""
    return "ok" if outcome == "success" else "error"


def _normalize_client_ip(value: str | None) -> str | None:
    """Return a structured actor IP only when a real value is available."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "unknown":
        return None
    return cleaned


class _CompatJsonlSink(AuditSink):
    """File sink retaining legacy top-level keys for existing consumers/tests."""

    def __init__(self, log_path: Path) -> None:
        """Initialise the instance state."""
        self._log_path = log_path
        path_utils.mkdir(str(self._log_path.parent))

    def emit(self, event: PlatformAuditEvent) -> None:
        """Execute emit."""
        payload = event.to_dict()
        details = payload.get("details", {})
        if not isinstance(details, dict):
            details = {}
        legacy_details = details.get("details", {})
        if not isinstance(legacy_details, dict):
            legacy_details = {}
        payload.update(
            {
                # Legacy compatibility fields retained during migration.
                "tool": details.get("tool", ""),
                "status": _to_legacy_status(str(payload.get("outcome", "error"))),
                "outcome": details.get(
                    "legacy_outcome",
                    _to_legacy_status(str(payload.get("outcome", "error"))),
                ),
                "profile": details.get("profile"),
                "session_id": details.get("session_id"),
                "client_ip": details.get("client_ip"),
                "duration_ms": payload.get("duration_ms"),
                "params": details.get("params", {}),
                "paths": details.get("paths", {}),
                "details": legacy_details,
            }
        )
        from cloud_dog_storage.backends.local import LocalStorage as _AuditLocalStorage
        _audit_storage = _AuditLocalStorage(root_path=self._log_path.parent, min_free_bytes=0)
        _audit_storage.append_text(
            self._log_path.name,
            json.dumps(payload, ensure_ascii=False) + "\n",
        )

    def flush(self) -> None:
        """Execute flush."""
        return

    def close(self) -> None:
        """Execute close."""
        return


class AuditLogger:
    """Compatibility audit logger that emits PS-40 events via cloud_dog_logging."""

    def __init__(
        self,
        log_path: Path,
        *,
        service_name: str = "file-mcp-server",
        service_instance: str = "file-mcp-local",
        environment: str = "dev",
    ) -> None:
        """Initialise the instance state."""
        redaction = RedactionEngine(
            presets=[BUILTIN_PRESETS["default"], BUILTIN_PRESETS["file_tools"]]
        )
        sink = _CompatJsonlSink(log_path)
        self._service_name = service_name
        self._service_instance = service_instance
        self._environment = environment
        self._logger = PlatformAuditLogger(
            redaction_engine=redaction,
            service_name=service_name,
            sink=sink,
        )

    def _bind_context(self) -> None:
        set_service_name(self._service_name)
        set_service_instance(self._service_instance)
        set_environment(self._environment)

    def write(self, event: FileAuditEvent) -> None:
        """Execute write."""
        self._bind_context()
        detail_payload: Dict[str, Any] = {
            "tool": event.tool,
            "profile": event.profile,
            "session_id": event.session_id,
            "client_ip": event.client_ip,
            "params": event.params,
            "paths": event.paths,
            "details": event.details,
            "legacy_status": event.status,
            "legacy_outcome": event.outcome,
        }
        platform_event = PlatformAuditEvent(
            timestamp=event.timestamp,
            event_type="tool_call",
            actor=Actor(
                type=event.actor_type or "service",
                id=event.actor_id or event.profile or self._service_name,
                ip=_normalize_client_ip(event.client_ip),
            ),
            action=event.action,
            outcome=_to_outcome(event.outcome or event.status),
            correlation_id=get_correlation_id(),
            service=self._service_name,
            service_instance=self._service_instance,
            environment=self._environment,
            target=Target(type="tool", id=event.tool),
            details=detail_payload,
            duration_ms=(
                int(round(event.duration_ms))
                if isinstance(event.duration_ms, (int, float))
                else None
            ),
        )
        self._logger.emit(platform_event)

    def flush(self) -> None:
        """Execute flush."""
        self._logger.flush()

    def close(self) -> None:
        """Execute close."""
        self._logger.close()


def build_event(
    *,
    tool: str,
    action: str,
    status: str,
    outcome: Optional[str] = None,
    profile: Optional[str] = None,
    session_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    duration_ms: Optional[float] = None,
    actor_id: Optional[str] = None,
    actor_type: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    paths: Optional[Dict[str, str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Build event."""
    return FileAuditEvent(
        tool=tool,
        action=action,
        status=status,
        outcome=outcome or status,
        profile=profile,
        session_id=session_id,
        client_ip=client_ip,
        duration_ms=duration_ms,
        actor_id=actor_id,
        actor_type=actor_type,
        params=params or {},
        paths=paths or {},
        details=details or {},
    )


AuditEvent = FileAuditEvent
