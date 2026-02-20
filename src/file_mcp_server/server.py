"""Server compatibility exports.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Thin compatibility layer re-exporting runtime server symbols.
Requirements: FR1.1, FR1.2, FR1.23, FR1.24
Tasks: T14, T15
Architecture: 5. Tool Interface
Tests: UT1.17, IT1.1, IT1.8
Recent Change History:
- 2026-02-20: Decomposed monolithic runtime into server_runtime module (API-KIT migration).
"""

from __future__ import annotations

from .server_runtime import (
    HealthCheckMiddleware,
    HttpRuntimeSettings,
    JsonRpcError,
    RequestContextMiddleware,
    StdioServer,
    StreamableHttpAcceptCompatibilityMiddleware,
    build_fastmcp_server,
    build_tool_registry,
    complete_oauth_callback,
    register_tools_with_fastmcp,
    resolve_http_settings,
    run_fastmcp_http_server,
)

__all__ = [
    "HealthCheckMiddleware",
    "HttpRuntimeSettings",
    "JsonRpcError",
    "RequestContextMiddleware",
    "StdioServer",
    "StreamableHttpAcceptCompatibilityMiddleware",
    "build_fastmcp_server",
    "build_tool_registry",
    "complete_oauth_callback",
    "register_tools_with_fastmcp",
    "resolve_http_settings",
    "run_fastmcp_http_server",
]
