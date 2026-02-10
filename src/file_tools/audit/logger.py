"""Audit logger scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import json


@dataclass
class AuditEvent:
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


class AuditLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: AuditEvent) -> None:
        payload = json.dumps(event.__dict__, ensure_ascii=False)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")


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
