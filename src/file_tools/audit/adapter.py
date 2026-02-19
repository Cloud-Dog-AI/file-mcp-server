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

from cloud_dog_logging.audit_logger import (  # type: ignore[import-untyped]
    AuditLogger as PlatformAuditLogger,
)
from cloud_dog_logging.audit_schema import (  # type: ignore[import-untyped]
    Actor,
    AuditEvent as PlatformAuditEvent,
    Target,
)
from cloud_dog_logging.correlation import get_correlation_id  # type: ignore[import-untyped]
from cloud_dog_logging.presets import BUILTIN_PRESETS  # type: ignore[import-untyped]
from cloud_dog_logging.redaction import RedactionEngine  # type: ignore[import-untyped]
from cloud_dog_logging.sinks.base import AuditSink  # type: ignore[import-untyped]


@dataclass
class AuditEvent:
    """Legacy-compatible domain event shape for file-mcp audit emission."""

    tool: str
    action: str
    status: str
    outcome: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    profile: Optional[str] = None
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    duration_ms: Optional[float] = None
    params: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


def _to_outcome(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"success", "ok"}:
        return "success"
    if normalized in {"failure", "failed"}:
        return "failure"
    return "error"


def _to_legacy_status(outcome: str) -> str:
    return "ok" if outcome == "success" else "error"


class _CompatJsonlSink(AuditSink):
    """File sink retaining legacy top-level keys for existing consumers/tests."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: PlatformAuditEvent) -> None:
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
                "profile": details.get("profile"),
                "session_id": details.get("session_id"),
                "client_ip": details.get("client_ip"),
                "params": details.get("params", {}),
                "paths": details.get("paths", {}),
                "details": legacy_details,
            }
        )
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        return

    def close(self) -> None:
        return


class AuditLogger:
    """Compatibility audit logger that emits PS-40 events via cloud_dog_logging."""

    def __init__(
        self, log_path: Path, *, service_name: str = "file-mcp-server"
    ) -> None:
        redaction = RedactionEngine(
            presets=[BUILTIN_PRESETS["default"], BUILTIN_PRESETS["file_tools"]]
        )
        sink = _CompatJsonlSink(log_path)
        self._service_name = service_name
        self._logger = PlatformAuditLogger(
            redaction_engine=redaction,
            service_name=service_name,
            sink=sink,
        )

    def write(self, event: AuditEvent) -> None:
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
            actor=Actor(type="service", id=event.profile or self._service_name),
            action=event.action,
            outcome=_to_outcome(event.outcome or event.status),
            correlation_id=get_correlation_id(),
            service=self._service_name,
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
        self._logger.flush()

    def close(self) -> None:
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
    params: Optional[Dict[str, Any]] = None,
    paths: Optional[Dict[str, str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    return AuditEvent(
        tool=tool,
        action=action,
        status=status,
        outcome=outcome or status,
        profile=profile,
        session_id=session_id,
        client_ip=client_ip,
        duration_ms=duration_ms,
        params=params or {},
        paths=paths or {},
        details=details or {},
    )
