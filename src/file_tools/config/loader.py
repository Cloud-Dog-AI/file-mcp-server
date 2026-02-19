"""Compatibility shim for legacy config loader imports.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Backward-compatible wrapper re-exporting adapter entry points.
Requirements: NF1.7
Tasks: T18
Architecture: 3.3 Example schema
Tests: UT1.1
Recent Change History:
- 2026-02-19: Replaced bespoke loader with cloud_dog_config adapter shim.
"""

from __future__ import annotations

from .adapter import get_profile, load_config

__all__ = ["get_profile", "load_config"]
