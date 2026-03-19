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
