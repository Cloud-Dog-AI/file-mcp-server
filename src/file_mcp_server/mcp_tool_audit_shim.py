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
# WITHOUT WARRANTIES OR ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""PS-50 MCP tool audit shim until cloud-dog-api-kit wheel includes mcp.tool_audit.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Provides the API-kit MCP audit middleware contract for older wheels.
Requirements: FR1.19, CS1.4
Tasks: W28A-101a
Architecture: API-kit compatibility shim
Tests: ST1, IT1, QT1
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from cloud_dog_logging import get_logger  # type: ignore[import-untyped]

_DEFAULT_REDACT_FIELDS = frozenset({
    "password", "secret", "token", "api_key", "credential", "auth",
    "access_token", "refresh_token", "key_hash",
})


def _redact_params(
    params: dict[str, Any],
    redact_fields: frozenset[str],
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if key.lower() in redact_fields:
            cleaned[key] = "[REDACTED]"
        else:
            cleaned[key] = value
    return cleaned


def mcp_tool_audit_middleware(
    tool_name: str,
    handler: Callable[..., Any],
    *,
    service: str,
    logger: Optional[Any] = None,
    redact_fields: Optional[frozenset[str]] = None,
) -> Callable[..., Any]:
    effective_redact = _DEFAULT_REDACT_FIELDS | (redact_fields or frozenset())
    log = logger or get_logger(f"cloud_dog_api_kit.mcp.audit.{service}")

    def _wrapped(**kwargs: Any) -> Any:
        correlation_id = str(uuid.uuid4().hex[:16])
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        safe_params = _redact_params(kwargs, effective_redact)
        t0 = time.monotonic()
        try:
            result = handler(**kwargs)
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.info(
                "mcp_tool_call",
                extra={
                    "event_type": "mcp_tool_call",
                    "correlation_id": correlation_id,
                    "service": service,
                    "tool_name": tool_name,
                    "parameters": safe_params,
                    "outcome": "success",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                },
            )
            return result
        except Exception as exc:
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.warning(
                "mcp_tool_call",
                extra={
                    "event_type": "mcp_tool_call",
                    "correlation_id": correlation_id,
                    "service": service,
                    "tool_name": tool_name,
                    "parameters": safe_params,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                    "error_detail": str(exc),
                },
            )
            raise

    _wrapped.__name__ = handler.__name__ if hasattr(handler, "__name__") else tool_name
    _wrapped.__doc__ = handler.__doc__
    return _wrapped
