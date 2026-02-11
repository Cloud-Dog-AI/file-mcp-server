"""Audit logging package (scaffold)."""

from .logger import AuditEvent, AuditLogger, build_event
from .snapshots import (
    create_snapshot,
    create_snapshot_bytes,
    prune_snapshots,
    snapshot_path,
    snapshot_path_for_logical,
)

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "build_event",
    "create_snapshot",
    "create_snapshot_bytes",
    "prune_snapshots",
    "snapshot_path",
    "snapshot_path_for_logical",
]
