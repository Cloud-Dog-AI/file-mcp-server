"""Compatibility shim for migrated audit logging.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Re-exports cloud_dog_logging-backed audit adapter symbols.
Requirements: FR1.3, FR1.8
Tasks: T18
Architecture: 7.4 Observability
Tests: ST1.6
Recent Change History:
- 2026-02-19: Replaced bespoke audit implementation with adapter re-export.
"""

from __future__ import annotations

from .adapter import AuditEvent, AuditLogger, build_event

__all__ = ["AuditEvent", "AuditLogger", "build_event"]
