"""Audit logging package (scaffold)."""

from .logger import AuditEvent, AuditLogger, build_event
from .snapshots import create_snapshot, snapshot_path

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "build_event",
    "create_snapshot",
    "snapshot_path",
]
