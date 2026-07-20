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

"""Server transport and runtime integration.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: FastMCP runtime wiring, tool registration, and legacy stdio dispatch.
Requirements: FR1.1, FR1.2, FR1.23, FR1.24
Tasks: T14, T15
Architecture: 5. Tool Interface
Tests: UT1.17, IT1.1, IT1.8
Recent Change History:
- 2026-02-07: Added FastMCP HTTP/SSE runtime, health endpoint middleware, and tool wiring.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, TextIO
from threading import RLock
from html import escape
from types import SimpleNamespace

import asyncio
import base64
import inspect
import json
import mimetypes
import uvicorn
import os
import pwd
import resource
import secrets
import sys
import time
import uuid
from urllib.parse import parse_qs, urlsplit
import re
from os import getenv as read_env_var

from cloud_dog_storage import path_utils

from cloud_dog_api_kit import create_app as create_api_kit_app, create_health_router  # type: ignore[import-not-found,import-untyped]
from cloud_dog_api_kit.a2a.card import A2ASkill
from cloud_dog_api_kit.a2a.events import (  # W28A-1002-APPLY-A — CFG-06 platform primitive
    ConfigChangeEvent,
    InMemoryEventBroadcaster,
)


_CFG06_REDACT_KEYS = frozenset({"api_key", "secret", "token", "password", "access_token"})


def _redact_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """CFG-06: redact secret-like keys before broadcasting a change event."""
    return {k: v for k, v in payload.items() if k not in _CFG06_REDACT_KEYS}


def _jsonish_model_dump(value: Any) -> Any:
    """Return a JSON-like representation for Pydantic models and containers."""
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            return value.model_dump(mode="json", exclude_none=False)
        except Exception:
            return {}
    if isinstance(value, dict):
        return {str(k): _jsonish_model_dump(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonish_model_dump(v) for v in value]
    return value


def _effective_config_leaf_paths(value: Any, path: str = "") -> list[str]:
    """Return public JsonExplorer key paths for all effective config leaves."""
    if isinstance(value, dict):
        paths: list[str] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            paths.extend(_effective_config_leaf_paths(child, child_path))
        return paths
    if isinstance(value, list):
        paths = []
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            paths.extend(_effective_config_leaf_paths(child, child_path))
        return paths
    return [path]


def _effective_config_path_segments(path: str) -> list[str]:
    return [
        segment
        for segment in re.split(r"\.|\[\d+\]", path)
        if segment
    ]


def _effective_config_is_secret_path(path: str) -> bool:
    segments = _effective_config_path_segments(path)
    secret_names = {
        "api_keys",
        "access_key",
        "secret_key",
        "password",
        "client_secret",
        "refresh_token",
        "access_token",
        "token",
        "api_key",
        "secret",
    }
    return any(segment.lower() in secret_names for segment in segments)


def _effective_config_redact(value: Any, sources: dict[str, dict[str, Any]], path: str = "") -> Any:
    """Mask secret leaves while preserving the config tree shape."""
    if isinstance(value, dict):
        return {
            str(key): _effective_config_redact(
                child,
                sources,
                f"{path}.{key}" if path else str(key),
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _effective_config_redact(child, sources, f"{path}[{index}]")
            for index, child in enumerate(value)
        ]
    if sources.get(path, {}).get("secret"):
        return "--------"
    return value


def _effective_config_server_scope(path: str) -> list[str]:
    first = path.split(".", 1)[0]
    if first == "api_server":
        return ["api"]
    if first == "web_server":
        return ["webui"]
    if first == "mcp_server":
        return ["mcp"]
    if first == "a2a_server":
        return ["a2a"]
    return ["shared"]
from cloud_dog_api_kit.web.proxy import WebApiProxy
from cloud_dog_idam.audit.emitter import AuditEmitter  # type: ignore[import-not-found,import-untyped]
from cloud_dog_config.yaml_loader import load_yaml  # type: ignore[import-untyped]
from cloud_dog_logging import get_logger  # type: ignore[import-untyped]
from cloud_dog_api_kit.correlation.context import (  # type: ignore[import-not-found,import-untyped]
    get_correlation_id as get_api_kit_correlation_id,
    set_correlation_id as set_api_kit_correlation_id,
    set_request_id as set_api_kit_request_id,
)
from cloud_dog_api_kit.envelopes import error_envelope  # type: ignore[import-not-found,import-untyped]
from cloud_dog_logging.correlation import (  # type: ignore[import-untyped]
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from file_tools.config.models import (
    HttpServerConfig,
    ProfileConfig,
    ServerConfig,
    ValidationConfig,
)
from file_tools.config.adapter import load_config
from file_tools.audit import (
    AuditLogger,
    build_event,
    create_snapshot,
    create_snapshot_bytes,
    prune_snapshots,
)
from file_tools.diff import diff_text, launch_meld
from file_tools.edit import (
    delete_matching_lines,
    html_set,
    json_copy,
    insert_after_line,
    insert_before_line,
    json_delete,
    json_get,
    json_merge,
    json_move,
    json_set,
    md_get_section,
    md_set_frontmatter,
    md_set_section,
    replace_line_range,
    replace_regex,
    xml_set,
    yaml_copy,
    yaml_delete,
    yaml_get,
    yaml_merge,
    yaml_move,
    yaml_set,
)
from file_tools.io import (
    b64_decode,
    b64_encode,
)
from file_tools.scope import ScopePolicy, PosixScopePolicy
from file_tools.search import search_content, search_paths
from file_tools.storage import NotSupportedError, build_storage_backend
from file_tools.tools import ToolDefinition, ToolMeta, ToolRegistry
from file_tools.tools.definitions import ToolSchema
from file_tools.convert import (
    BackendCannotHandleError,
    BackendNotFoundError,
    BackendUnavailableError,
    ConversionError,
    convert_file as run_convert_file,
)
from file_tools.limits import (
    LimitError,
    call_with_timeout,
    enforce_timeout,
    raise_if_operation_cancelled,
)
from file_tools.validate.policy import validate_with_mode
from starlette.requests import HTTPConnection
from mcp.server.auth.middleware.auth_context import get_access_token

from .auth import MultiProfileApiKeyTokenVerifier, get_request_profile_name, set_request_profile_name
from .endpoint_health import ENDPOINT_HEALTH_MANAGER
from .db import (
    PlatformDatabaseRuntime,
    database_health,
    initialise_database,
    shutdown_database,
)
from .db.models import FileStorageProfile
from .jobs_runtime import FileMcpJobsRuntime
from .google_drive_admin import (
    MASKED_CLIENT_SECRET,
    begin_oauth,
    complete_oauth_callback,
    parse_form_urlencoded,
    render_link_success_page,
    render_setup_page,
)
from .admin_identity import AdminIdentityError, AdminIdentityService
from .web_flat_roles import (
    ADMIN_ROLE as FLAT_ADMIN_ROLE,
    READ_ONLY_ROLE as FLAT_READ_ONLY_ROLE,
    READ_WRITE_ROLE as FLAT_READ_WRITE_ROLE,
    normalise_flat_role,
    permissions_for_role,
    role_can_write,
    role_is_admin,
)

OOB_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
_REQUEST_SESSION_ID: ContextVar[str | None] = ContextVar(
    "file_mcp_request_session_id", default=None
)
_REQUEST_CLIENT_IP: ContextVar[str | None] = ContextVar(
    "file_mcp_request_client_ip", default=None
)


# ── W28E-1870-B: process-shared storage change-watch adapter ────────────────
# The MCP ``file_watch_*`` tools (built into the per-profile seed registry) and
# the REST ``/v1/watches*`` surface + server-mediated capture shim (on the ASGI
# middleware) MUST operate on the SAME set of watches. The middleware owns the
# fully-wired instance (durable SqlJournal engine + a2a.events broadcaster +
# audit sink) and publishes it here; the registry tools read it back. Until the
# middleware publishes one, a lazily-built in-memory fallback keeps the MCP
# tools functional (e.g. stdio-only deployments with no HTTP server).
_SHARED_WATCH_SERVICE: Any | None = None


def set_shared_watch_service(service: Any) -> None:
    """Publish the fully-wired WatchService for the MCP tool family to consume."""
    global _SHARED_WATCH_SERVICE
    _SHARED_WATCH_SERVICE = service


def get_shared_watch_service() -> Any:
    """Return the process-shared WatchService (lazily building an in-memory one)."""
    global _SHARED_WATCH_SERVICE
    if _SHARED_WATCH_SERVICE is None:
        from file_tools.change_stream import WatchService

        _SHARED_WATCH_SERVICE = WatchService()
    return _SHARED_WATCH_SERVICE


def get_request_session_id() -> str | None:
    """Return request session id."""
    return _REQUEST_SESSION_ID.get()


def get_request_client_ip() -> str | None:
    """Return request client ip."""
    return _REQUEST_CLIENT_IP.get()


@dataclass(frozen=True)
class JsonRpcError:
    code: int
    message: str


class LogLike(Protocol):
    """Protocol for logger methods consumed by runtime handlers."""

    def info(self, msg: str, **extra: Any) -> None: ...

    def warning(self, msg: str, **extra: Any) -> None: ...

    def error(self, msg: str, **extra: Any) -> None: ...

    def exception(self, msg: str, **extra: Any) -> None: ...


@dataclass(frozen=True)
class HttpRuntimeSettings:
    transport: str
    host: str
    port: int
    mcp_path: str
    health_path: str
    events_path: str
    stateless_http: bool


def _resolve_auth_api_key_value(raw_value: str, **_unused_clients: Any) -> str:
    """Resolve API-key values, including nested env placeholders.

    Extra client arguments are accepted for backward compatibility with
    existing tests/call-sites and are intentionally unused here.
    """
    del _unused_clients
    value = str(raw_value or "").strip()
    if not value:
        return ""

    for _ in range(8):
        if not (value.startswith("${") and value.endswith("}")):
            break
        key = value[2:-1].strip()
        if not key:
            return ""
        resolved = str(read_env_var(key, "")).strip()
        if not resolved:
            return ""
        value = resolved

    if "${" in value:
        return ""
    return value


def _build_profile_auth_map(
    config: ServerConfig,
) -> dict[str, tuple[list[str], str | None, str | None]]:
    """Build per-profile auth mapping with resolved API-key values."""
    profile_auth: dict[str, tuple[list[str], str | None, str | None]] = {}
    for name, profile in config.profiles.items():
        resolved_keys = [
            resolved
            for resolved in (
                _resolve_auth_api_key_value(str(item))
                for item in profile.auth.api_keys
            )
            if resolved
        ]
        profile_auth[name] = (
            resolved_keys,
            profile.auth.header_name,
            profile.auth.header_scheme,
        )
    return profile_auth


def _deleted_profile_name(name: str) -> str:
    """Build a unique tombstone name for soft-deleted profile rows."""
    base = str(name).strip() or "profile"
    suffix = f"__deleted_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    max_base_length = max(1, 128 - len(suffix))
    return f"{base[:max_base_length]}{suffix}"


def _profile_config_to_mapping(
    profile: ProfileConfig | dict[str, Any] | None,
) -> dict[str, Any]:
    """Convert a profile model into a JSON-serialisable mapping."""
    if profile is None:
        return {}
    if isinstance(profile, dict):
        return json.loads(json.dumps(profile))
    try:
        payload = profile.model_dump(mode="json", exclude_none=True)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalise_profile_mapping(
    profile: dict[str, Any] | None,
    *,
    fallback_profile: ProfileConfig | dict[str, Any] | None = None,
    default_profile: ProfileConfig | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fill required auth fields from the profile/default fallback configuration."""
    normalized = json.loads(json.dumps(profile if isinstance(profile, dict) else {}))
    auth = normalized.get("auth")
    if not isinstance(auth, dict):
        auth = {}

    fallback_auth_sources: list[dict[str, Any]] = []
    for source in (fallback_profile, default_profile):
        source_mapping = _profile_config_to_mapping(source)
        source_auth = source_mapping.get("auth")
        if isinstance(source_auth, dict):
            fallback_auth_sources.append(source_auth)

    api_keys = [str(item).strip() for item in (auth.get("api_keys") or []) if str(item).strip()]
    if not api_keys:
        for source_auth in fallback_auth_sources:
            candidate_keys = [
                str(item).strip()
                for item in (source_auth.get("api_keys") or [])
                if str(item).strip()
            ]
            if candidate_keys:
                api_keys = candidate_keys
                break

    header_name = str(auth.get("header_name") or "").strip()
    if not header_name:
        for source_auth in fallback_auth_sources:
            candidate = str(source_auth.get("header_name") or "").strip()
            if candidate:
                header_name = candidate
                break

    header_scheme = str(auth.get("header_scheme") or "").strip()
    if not header_scheme:
        for source_auth in fallback_auth_sources:
            candidate = str(source_auth.get("header_scheme") or "").strip()
            if candidate:
                header_scheme = candidate
                break

    merged_auth = json.loads(json.dumps(auth))
    merged_auth["api_keys"] = api_keys
    if header_name:
        merged_auth["header_name"] = header_name
    if header_scheme:
        merged_auth["header_scheme"] = header_scheme
    normalized["auth"] = merged_auth
    return normalized


def _merge_active_db_profiles_into_config(
    config: ServerConfig,
    *,
    db_runtime: PlatformDatabaseRuntime | None,
    logger: LogLike | None = None,
) -> ServerConfig:
    """Merge active DB profiles into config with DB rows taking precedence."""
    if db_runtime is None:
        return config

    with db_runtime.session_manager.session() as session:
        rows = session.query(FileStorageProfile).filter_by(is_active=True).all()
        updated_rows = False
        default_profile = config.profiles.get("default")

        for row in rows:
            try:
                raw_config = json.loads(row.config_json) if row.config_json else {}
            except Exception:
                raw_config = {}
            normalized_config = _normalise_profile_mapping(
                raw_config,
                fallback_profile=config.profiles.get(row.name),
                default_profile=default_profile,
            )
            if normalized_config != raw_config:
                row.config_json = json.dumps(normalized_config)
                updated_rows = True
            try:
                profile_config = ProfileConfig.model_validate(normalized_config)
            except Exception:
                if logger:
                    logger.warning(
                        "Skipping invalid DB profile config",
                        profile_name=row.name,
                    )
                continue
            config.profiles[row.name] = profile_config

        if updated_rows:
            session.commit()
    return config


def _build_response(
    request_id: Any, result: Any = None, error: JsonRpcError | None = None
) -> Dict[str, Any]:
    """Handle build response."""
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": error.code, "message": error.message}
    else:
        payload["result"] = result
    return payload


def _tool_input_schema(tool: ToolDefinition) -> dict[str, Any]:
    """Return MCP-compatible input schema for a tool definition."""
    model = tool.schema_def.input_model
    if model is not None:
        try:
            schema = model.model_json_schema()
            if isinstance(schema, dict):
                return schema
        except Exception:
            pass
    return {"type": "object", "properties": {}}


def _tool_payload(tool: ToolDefinition) -> dict[str, Any]:
    """Serialise a tool definition for tools/list responses."""
    return {
        "name": tool.meta.name,
        "description": tool.meta.description,
        "mutating": tool.meta.mutating,
        "requires_validation": tool.meta.requires_validation,
        "supports_dry_run": tool.meta.supports_dry_run,
        "inputSchema": _tool_input_schema(tool),
    }


def _mcp_initialize_payload(
    *,
    protocol_version: str,
    server_name: str,
    server_version: str,
) -> dict[str, Any]:
    """Build a minimal MCP initialize result for streamable clients."""
    negotiated = str(protocol_version or "").strip() or "2025-11-25"
    return {
        "protocolVersion": negotiated,
        "capabilities": {
            "tools": {},
            "resources": {},
        },
        "serverInfo": {
            "name": server_name,
            "version": server_version,
        },
    }


def _mcp_tool_call_payload(result: Any) -> dict[str, Any]:
    """Wrap a service tool result into an MCP-compatible CallTool payload."""
    if isinstance(result, dict) and isinstance(result.get("content"), list):
        return result
    if isinstance(result, list) and all(
        isinstance(item, dict) and "type" in item for item in result
    ):
        return {"content": result}

    if isinstance(result, str):
        content_text = result
    else:
        content_text = json.dumps(result, default=str)

    payload: dict[str, Any] = {
        "content": [{"type": "text", "text": content_text}],
    }
    if not isinstance(result, str):
        payload["structuredContent"] = result
    return payload


def _api_error_list_envelope(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    """Build API-KIT-based error envelope compatible with migration contract."""
    correlation_id = (
        get_correlation_id() or get_api_kit_correlation_id() or uuid.uuid4().hex
    )
    payload = error_envelope(
        code=code,
        message=message,
        details=details,
        retryable=retryable,
        correlation_id=correlation_id,
    )
    error = payload.get("error", {})
    return {
        "ok": False,
        "errors": [
            {
                "code": error.get("code", code),
                "message": error.get("message", message),
                "details": error.get("details"),
                "retryable": bool(error.get("retryable", retryable)),
            }
        ],
        "meta": {
            "correlation_id": payload.get("meta", {}).get("correlation_id"),
            "request_id": payload.get("meta", {}).get("request_id"),
        },
    }


class DispatchError(RuntimeError):
    """Raised when a request cannot be dispatched."""


def _resolve_complete_oauth_callback():
    """Resolve callback through server compatibility module for monkeypatch support."""
    try:
        from . import server as server_module

        candidate = getattr(server_module, "complete_oauth_callback", None)
        if callable(candidate):
            return candidate
    except Exception:
        pass
    return complete_oauth_callback


class StdioServer:
    """Legacy stdio transport for compatibility with existing tests."""

    def __init__(self, registry: ToolRegistry) -> None:
        """Initialise the instance state."""
        self.registry = registry

    def handle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute handle request."""
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if not method:
            return _build_response(
                request_id, error=JsonRpcError(-32600, "Missing method")
            )

        try:
            if method == "tools/list":
                tools = [_tool_payload(tool) for tool in self.registry.list_tools()]
                return _build_response(request_id, result=tools)
            if method == "tools/call":
                from file_tools.tools.schemas import normalize_and_filter_tool_args
                name = params.get("name")
                if not name:
                    raise DispatchError("Missing tool name")
                tool = self.registry.get(name)
                arguments = normalize_and_filter_tool_args(
                    params.get("arguments") or {}, tool.handler
                )
                result = tool.handler(**arguments)
                return _build_response(request_id, result=result)
            raise DispatchError(f"Unknown method: {method}")
        except DispatchError as exc:
            return _build_response(request_id, error=JsonRpcError(-32601, str(exc)))
        except Exception as exc:  # pragma: no cover - defensive
            return _build_response(request_id, error=JsonRpcError(-32000, str(exc)))

    def serve(
        self,
        *,
        input_stream: Optional[TextIO] = None,
        output_stream: Optional[TextIO] = None,
    ) -> None:
        """Execute serve."""
        in_stream = input_stream or sys.stdin
        out_stream = output_stream or sys.stdout
        for line in in_stream:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                response = _build_response(None, error=JsonRpcError(-32700, str(exc)))
            else:
                response = self.handle_request(payload)
            out_stream.write(json.dumps(response) + "\n")
            out_stream.flush()


# W28E-1863 fix-wave-b (CC-401 for file-mcp): reserved server-side path prefixes /
# exact paths that MUST NOT be served the SPA shell. These proxy to the API / MCP /
# A2A upstreams, are health/readiness probes, static assets, or auth/bootstrap
# endpoints. Everything ELSE that is a browser DOCUMENT navigation (an extensionless
# GET/HEAD) resolves — as the fallback of LAST RESORT — to the SPA index.html shell
# so React renders the requested route (or its own login gate for an anonymous
# visitor) instead of the inner ASGI app's raw 404 JSON. Adapted from the deployed,
# smoke-green chat-client ``ui_spa.is_spa_document_navigation`` BLOCKLIST (commit
# 2156ef9) and the sql-agent / search-mcp true-catch-all pattern (AGENT-LESSONS §2.4).
#
# CRITICAL (why this is a blocklist wired at the terminal fallthrough, NOT an
# Accept-header carve-out in mid-flow like the reverted fix-wave-a 85eb744): the
# fix-wave-a Accept approach let the backend API 401/404 SHADOW the SPA and produced
# a post-login BLANK render (smoke PDS-007). Here the check runs ONLY after every
# explicit API / MCP / A2A / health / auth / admin-gate / asset handler has had its
# chance to ``return`` — so it can never shadow them; it only catches paths that
# would otherwise fall through to the inner-app 404.
_RESERVED_NON_SPA_PREFIXES: frozenset[str] = frozenset(
    {
        "api",
        "v1",
        "webapi",
        "webmcp",
        "mcp",
        "messages",
        "weba2a",
        "a2a",
        "events",
        "tasks",
        "sessions",
        "auth",
        "assets",
        "files",
        "idam",
        ".well-known",
        # /login itself is an explicit SPA route (served above); /login/<x> bootstrap
        # is auth. Reserving the prefix keeps the SPA /login handled by its own route.
        "login",
    }
)
_RESERVED_NON_SPA_EXACT: frozenset[str] = frozenset(
    {
        "health",
        "ready",
        "live",
        "status",
        "version",
        "openapi",
        "runtime-config.js",
        "favicon.ico",
        "apple-touch-icon.png",
        "apple-touch-icon-precomposed.png",
        "robots.txt",
        "sitemap.xml",
    }
)


def is_spa_document_navigation(path: str) -> bool:
    """Return True when a browser GET/HEAD for ``path`` should serve the SPA shell.

    A path is a SPA document navigation when it is NOT one of the reserved
    server-side surfaces (API / MCP / A2A proxy paths, health/readiness probes,
    auth/bootstrap endpoints, static assets) and does NOT look like a static file
    request (no ``.`` in the final path segment — those are asset/file GETs handled
    by the dedicated asset routes or a genuine 404). This is the fallback of last
    resort that guarantees every React history route — including ones not present in
    the enumerated ``_ui_route_paths`` allowlist (e.g. bare ``/admin``,
    ``/system/preferences``, ``/research``) — resolves to ``index.html`` on a hard
    navigation / refresh / bookmark, so the SPA renders (unauthenticated -> its own
    login gate) rather than leaking the inner ASGI app's raw 404 JSON body.
    """
    cleaned = str(path or "").strip().strip("/")
    if not cleaned:
        # Bare "/" is served by the explicit UI-route handler above; treat as
        # non-doc here so this fallback never double-handles the root.
        return False
    first_segment = cleaned.split("/", 1)[0]
    if first_segment in _RESERVED_NON_SPA_PREFIXES:
        return False
    if cleaned in _RESERVED_NON_SPA_EXACT or first_segment in _RESERVED_NON_SPA_EXACT:
        return False
    # A dot in the LAST segment indicates a static file request (e.g. foo.js,
    # sitemap.xml) — never serve those the HTML shell; let the asset routes or a
    # genuine 404 handle them.
    if "." in cleaned.rsplit("/", 1)[-1]:
        return False
    return True


class HealthCheckMiddleware:
    """Minimal unauthenticated health endpoint for transport app."""

    def __init__(
        self,
        app,
        *,
        health_path: str,
        profile_name: str,
        transport: str,
        config: ServerConfig | None = None,
        reload_callback=None,
        registry_provider=None,
        mcp_path: str = "/mcp",
        a2a_auth_verifier=None,
        db_runtime: PlatformDatabaseRuntime | None = None,
        admin_identity_service: AdminIdentityService | None = None,
        jobs_runtime_provider: Callable[[str | None], FileMcpJobsRuntime | None]
        | None = None,
        callback_host_fallback: str = "",
        web_sessions: dict[str, dict] | None = None,
        cookie_name: str = "file_web_session",
        config_event_broadcaster: Optional[InMemoryEventBroadcaster] = None,
    ) -> None:
        """Initialise the instance state."""
        self.app = app
        self.health_path = health_path
        self.profile_name = profile_name
        self.transport = transport
        self.config = config
        self.reload_callback = reload_callback
        self.registry_provider = registry_provider
        self.mcp_path = _normalize_path(mcp_path, default="/mcp")
        self.a2a_auth_verifier = a2a_auth_verifier
        self.db_runtime = db_runtime
        self.server_role = (
            str(read_env_var("FILE_MCP_ACTIVE_SERVER_ROLE") or "legacy").strip().lower()
            or "legacy"
        )
        # Session store for cookie-based WebUI login.
        self._sessions = web_sessions if web_sessions is not None else {}
        # W28C-1702 (FM6): bind each OAuth `state` to the principal that issued
        # it on /start, so /callback can reject a state replayed by a different
        # principal (state-replay mitigation).
        self._oauth_state_principal: dict[str, str] = {}
        # Thread-a (PROGRAM-IDAM-RECOVERY-2, W28A-728-R4) flat WebUI login
        # accounts: the three flat roles admin / read-write / read-only.
        #
        # W28A-SEC-R17: the public dev/test credential literals were removed from
        # source. The admin password now comes ONLY from the environment
        # (CLOUD_DOG_WEB_LOGIN_PASSWORD — injected on every deployed container),
        # and read-write / read-only fall back to the RESOLVED ADMIN password
        # when their own env override is unset (never a hardcoded string). This
        # keeps all three flat roles logging in out of the box while shipping no
        # credential value in source, and is strictly more secure (rw/ro stop
        # using a public value). An unset admin password fails closed: the
        # empty-password guard in _handle_auth_login rejects it, so no account
        # can authenticate with an empty secret. Usernames are non-secret
        # defaults. Roles/permissions come from the ONE shared cloud_dog_idam
        # guard (see web_flat_roles.py — no per-service RBAC fork).
        self._admin_username = read_env_var("CLOUD_DOG_WEB_LOGIN_USERNAME") or "admin"
        self._admin_password = read_env_var("CLOUD_DOG_WEB_LOGIN_PASSWORD") or ""
        self._rw_username = read_env_var("CLOUD_DOG_WEB_LOGIN_READ_WRITE_USERNAME") or "read-write"
        self._rw_password = read_env_var("CLOUD_DOG_WEB_LOGIN_READ_WRITE_PASSWORD") or self._admin_password
        self._ro_username = read_env_var("CLOUD_DOG_WEB_LOGIN_READ_ONLY_USERNAME") or "read-only"
        self._ro_password = read_env_var("CLOUD_DOG_WEB_LOGIN_READ_ONLY_PASSWORD") or self._admin_password
        # username -> (password, flat-role). Built once; the comparison in
        # _handle_auth_login is constant-time per candidate (secrets.compare_digest)
        # so a wrong username and a wrong password are indistinguishable.
        self._flat_accounts: dict[str, tuple[str, str]] = {
            self._admin_username: (self._admin_password, FLAT_ADMIN_ROLE),
            self._rw_username: (self._rw_password, FLAT_READ_WRITE_ROLE),
            self._ro_username: (self._ro_password, FLAT_READ_ONLY_ROLE),
        }
        self._cookie_name = cookie_name
        self.admin_identity_service = admin_identity_service
        self.jobs_runtime_provider = jobs_runtime_provider
        # W28A-1002-APPLY-A — CFG-06: A2A config-change broadcaster for admin CRUD.
        self.config_event_broadcaster = config_event_broadcaster
        # W28A-742 — lazy IDAM keystone dependencies. The chokepoint
        # (file_mcp_server.guard.check_route_guard) and the inline
        # /idam/v1/rbac/bindings handlers call _w28a742_idam_dependencies()
        # to obtain (engine, binding_repo, membership). Engine + membership
        # are cached; binding_repo is built per-call (fresh session).
        self._w28a742_engine = None
        self._w28a742_membership = None
        # PS-92 (W28A-970h-V2): prefer TEST_A2A_BASE_PATH (legacy test override),
        # then configured `a2a_server.base_path`, then canonical default. Distinct
        # from top-level `http.base_path` (transport listener base).
        _test_a2a_override = read_env_var("TEST_A2A_BASE_PATH")
        if _test_a2a_override:
            _a2a_config_base = _test_a2a_override
        else:
            _config_a2a = None
            if config is not None:
                _config_a2a = getattr(config.a2a_server, "base_path", None)
            _a2a_config_base = _config_a2a or "/a2a"
        self.a2a_base_path = _normalize_path(_a2a_config_base, default="/a2a")
        self.a2a_health_path = _join_paths(self.a2a_base_path, "/health")
        self.logger = get_logger("file_mcp_server.admin")
        self.app_name = "file-mcp-server"
        self.version = str(read_env_var("FILE_MCP_VERSION") or "").strip() or self._read_pyproject_version() or "0.0.0"
        self.env_file = str(read_env_var("FILE_MCP_ACTIVE_ENV_PATH") or "") or None
        self.active_config = str(
            read_env_var("FILE_MCP_ACTIVE_CONFIG_PATH") or "config.yaml"
        )
        self.profile_names = [
            name.strip()
            for name in (
                read_env_var("FILE_MCP_ACTIVE_PROFILE_NAMES") or profile_name
            ).split(",")
            if name.strip()
        ]
        # W28C-1702 (FM5): the env-derived list above is collapsed at startup.
        # main.py sets FILE_MCP_ACTIVE_PROFILE_NAMES from the config-FILE profiles
        # BEFORE _merge_active_db_profiles_into_config overlays the additional
        # active DB profiles, so /status.service_metrics.profile_count read 1. The
        # authoritative active-profile set is the DB-merged config this middleware
        # already holds; derive the list from it when present (the env list is the
        # fallback only when no config is wired, e.g. isolated unit tests).
        if config is not None and getattr(config, "profiles", None):
            self.profile_names = list(config.profiles.keys())
        assert len(self.profile_names) >= 1  # tripwire: must never collapse to 0
        self.logger.info(
            "profile_names_loaded",
            names=self.profile_names,
            count=len(self.profile_names),
        )
        self.admin_ui_enabled = _to_bool(
            read_env_var("FILE_MCP_ADMIN_UI_ENABLED"), default=False
        )
        self.admin_ui_token = str(read_env_var("FILE_MCP_ADMIN_UI_TOKEN") or "").strip()
        self.admin_apply_on_callback = _to_bool(
            read_env_var("FILE_MCP_ADMIN_APPLY_ON_CALLBACK"), default=True
        )

        # --- A2A skill handlers (W28A-742 — three catalogue skills) ---

        def _a2a_file_management(text: str) -> str:
            """Dispatch MCP tools via JSON: {\"tool\":\"list_files\",\"arguments\":{}}."""
            try:
                raw = text.strip()
                if not raw:
                    return (
                        "Provide JSON: {\"tool\":\"TOOL_NAME\",\"arguments\":{...}} "
                        "for any registered MCP tool (e.g. list_files, create_file)."
                    )
                payload = json.loads(raw) if raw.startswith("{") else {}
            except Exception as exc:
                return f"Invalid JSON: {exc}"
            if not isinstance(payload, dict):
                return "Payload must be a JSON object"
            tool = str(payload.get("tool") or "").strip()
            args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
            if not tool:
                return "Missing \"tool\" in JSON payload"
            if not callable(self.registry_provider):
                return "Error: tool registry unavailable"
            try:
                from file_tools.tools.schemas import normalize_and_filter_tool_args
                reg = self.registry_provider()
                tool_def = reg.get(tool)
                filtered = normalize_and_filter_tool_args(args, tool_def.handler)
                result = tool_def.handler(**filtered)
                return json.dumps(result, default=str)[:24000]
            except Exception as exc:
                return f"Error: {exc}"

        def _a2a_file_search(text: str) -> str:
            """Run search_files — JSON {\"query\":\"...\",\"path\":\".\"} or plain query string."""
            if not callable(self.registry_provider):
                return "Error: tool registry unavailable"
            try:
                raw = text.strip()
                if raw.startswith("{"):
                    payload = json.loads(raw)
                    q = str(payload.get("query") or "")
                else:
                    q = raw
                if not q:
                    return "Missing search query"
                reg = self.registry_provider()
                result = reg.get("search_paths").handler(query=q)
                return json.dumps(result, default=str)[:24000]
            except Exception as exc:
                return f"Error: {exc}"

        def _a2a_gdrive_sync(text: str) -> str:
            """Google Drive tools — JSON {\"tool\":\"gdrive_list\",\"arguments\":{}}."""
            try:
                raw = text.strip()
                payload = json.loads(raw) if raw.startswith("{") else {}
            except Exception as exc:
                return f"Invalid JSON: {exc}"
            if not isinstance(payload, dict):
                return "Payload must be JSON object"
            tool = str(payload.get("tool") or "gdrive_list").strip()
            args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
            if not callable(self.registry_provider):
                return "Error: tool registry unavailable"
            try:
                from file_tools.tools.schemas import normalize_and_filter_tool_args
                reg = self.registry_provider()
                tool_def = reg.get(tool)
                filtered = normalize_and_filter_tool_args(args, tool_def.handler)
                result = tool_def.handler(**filtered)
                return json.dumps(result, default=str)[:24000]
            except Exception as exc:
                return f"Error: {exc}"

        def _a2a_change_watch(text: str) -> str:
            """Storage change-watch — JSON {"op":"create|list|status|get_batch|ack|
            recover|pause|resume|delete|test_event","arguments":{...}} (PS-102 §5.4).

            One A2A skill per MCP verb: a listening agent creates a watch and
            consumes agent-consumable batches. Dispatches onto the process-shared
            WatchService (durable journal). Never blocks a worker (CSTREAM-002).
            """
            try:
                raw = text.strip()
                payload = json.loads(raw) if raw.startswith("{") else {}
            except Exception as exc:
                return f"Invalid JSON: {exc}"
            if not isinstance(payload, dict):
                return "Payload must be a JSON object"
            op = str(payload.get("op") or "list").strip()
            args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
            tool_name = f"file_watch_{op}"
            if not callable(self.registry_provider):
                return "Error: tool registry unavailable"
            try:
                reg = self.registry_provider()
                tool_def = reg.get(tool_name)
                result = tool_def.handler(**args)
                return json.dumps(result, default=str)[:24000]
            except Exception as exc:
                return f"Error: {exc}"

        # A2A agent card and task submission
        self._a2a_skills = [
            A2ASkill(
                id="file-management",
                name="file-management",
                description="Create, read, update, delete files and directories",
                handler=_a2a_file_management,
            ),
            A2ASkill(
                id="file-search",
                name="file-search",
                description="Search for files by name, content, or metadata",
                handler=_a2a_file_search,
            ),
            A2ASkill(
                id="gdrive-sync",
                name="gdrive-sync",
                description="Upload/download files from Google Drive",
                handler=_a2a_gdrive_sync,
            ),
            A2ASkill(
                id="change-watch",
                name="change-watch",
                description=(
                    "Subscribe to storage-profile changes: create/list/status/"
                    "get_batch/ack/recover/pause/resume/delete/test_event (PS-102)"
                ),
                handler=_a2a_change_watch,
            ),
        ]
        self._a2a_card = {
            "name": "file-mcp",
            "description": "File management and Google Drive integration agent",
            "url": "",
            "version": "1.0.0",
            "capabilities": {"streaming": False, "pushNotifications": False},
            "skills": [
                {"name": s.name, "description": s.description}
                for s in self._a2a_skills
            ],
        }
        self._a2a_skill_map = {s.id: s for s in self._a2a_skills}

        self.server_id = (
            str(read_env_var("FILE_MCP_SERVER_ID") or "").strip() or "file-mcp-local"
        )
        self.enable_legacy_api_alias = _to_bool(
            read_env_var("FILE_MCP_HTTP_ENABLE_LEGACY_API_ALIAS"), default=True
        )
        self.callback_host_fallback = callback_host_fallback.strip()
        self.ui_base_path = _normalize_path(
            read_env_var("FILE_MCP_UI_BASE_PATH"), default="/ui"
        )
        self.api_proxy = self._build_web_api_proxy()
        self._started_at = time.time()
        self._cpu_last_wall = time.monotonic()
        self._cpu_last_process = time.process_time()
        self._service_metrics_cache: tuple[float, dict[str, Any]] | None = None
        configured_ui_dist = str(read_env_var("FILE_MCP_UI_DIST_PATH") or "").strip()
        if configured_ui_dist:
            self.ui_dist_path = path_utils.as_path(path_utils.resolve_path(configured_ui_dist))
        else:
            self.ui_dist_path = path_utils.as_path(path_utils.resolve_path(__file__)).parents[2] / "ui" / "dist"
        self._status_roots = self._resolve_status_roots()
        self._login_access_token = self._resolve_login_access_token()
        self.web_mcp_path = "/webmcp"
        # ── W28E-1870-B storage change-watch adapter (PS-102 §4.1 / CSTREAM-FILE) ──
        # A thin adapter over the common cloud_dog_api_kit.change_stream foundation.
        # Journal is the durable SqlJournal on the service's cloud_dog_db engine so a
        # watch backlog survives restart (CSTREAM-007); live SSE fan-out reuses the
        # existing a2a.events broadcaster via make_broadcast_hook (no bespoke
        # broadcaster); audit rows land in the same stream as the rest of the service.
        self._watch_service = None  # lazily built on first access

    @property
    def watch_service(self):
        """Return the storage change-watch adapter (lazily built) — PS-102 §4.1.

        Built once, bound to the live cloud_dog_db engine + the existing a2a.events
        broadcaster + audit logger. Consumes the published change-stream foundation
        (RULES §1.4); this runtime holds no bespoke journal/cursor/queue.
        """
        if self._watch_service is None:
            from file_tools.change_stream import WatchService, make_audit_sink

            engine = None
            if self.db_runtime is not None:
                engine = getattr(self.db_runtime, "engine", None)
            audit_sink = None
            try:
                audit_sink = make_audit_sink(self.logger)
            except Exception:  # pragma: no cover - audit wiring must never block startup
                audit_sink = None
            self._watch_service = WatchService(
                engine=engine,
                broadcaster=self.config_event_broadcaster,
                audit_sink=audit_sink,
            )
            # Publish so the MCP file_watch_* tools operate on the same watches.
            set_shared_watch_service(self._watch_service)
        return self._watch_service

    def capture_storage_mutation(
        self,
        tool_name: str,
        arguments: dict,
        *,
        actor: str | None = None,
        correlation_id: str | None = None,
        profile_id: str = "default",
        backend: str = "",
    ) -> None:
        """Server-mediated capture hook for changes made THROUGH file-mcp.

        Called by the tool-dispatch shim after a mutation tool succeeds. Translates
        the tool verb into a canonical ChangeEvent candidate and fans it to matching
        live watches (PS-102 §6 native-first: no polling/scan, no busy-wait). Capture
        MUST NEVER crash the mutating request path — all errors are swallowed.
        """
        try:
            from file_tools.change_stream import TOOL_ACTION_MAP

            action = TOOL_ACTION_MAP.get(tool_name)
            if action is None:
                return
            path = str(
                arguments.get("path")
                or arguments.get("dst")
                or arguments.get("target")
                or arguments.get("dest")
                or ""
            )
            if not path:
                return
            old_path = str(arguments.get("src") or arguments.get("source") or "")
            self.watch_service.observe_change(
                tenant_id=str(profile_id or "default"),
                profile_id=str(profile_id or "default"),
                path=path,
                action=action,
                backend=str(backend or ""),
                old_path=old_path if action in {"renamed", "moved"} else "",
                actor=actor,
                correlation_id=correlation_id,
                capture="server_mediated",
            )
        except Exception:  # pragma: no cover - capture is best-effort, never fatal
            return

    @staticmethod
    def _read_pyproject_version() -> str:
        """Read version from pyproject.toml if available."""
        try:
            import tomllib
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                return ""
        try:
            pyproject = path_utils.as_path(path_utils.resolve_path(__file__)).parents[2] / "pyproject.toml"
            data = tomllib.loads(path_utils.read_text(str(pyproject)))
            return str(data.get("project", {}).get("version", ""))
        except Exception:
            return ""

    def _build_identity(self) -> dict[str, str]:
        """Return build/deploy identity for WSC-014 / PS-30 UI-R7.3.

        Source of truth is the container build (docker-build.sh stamps the image
        OCI ``org.opencontainers.image.revision`` label AND injects the matching
        runtime ENV: ``FILE_MCP_SOURCE_COMMIT`` / ``FILE_MCP_SOURCE_BRANCH`` /
        ``FILE_MCP_BUILD_DATE`` / ``FILE_MCP_CONTAINER_DIGEST``). All values are
        read config-routed via ``read_env_var`` (RULES §1.4.1 — no direct-env).
        For a dev/source run (no container ENV) ``source_commit`` falls back to the
        working-tree git HEAD so the About page is still populated locally.
        Modelled on search-mcp's build-identity reference. W28E-1863 fix-wave-b.
        """
        commit = str(read_env_var("FILE_MCP_SOURCE_COMMIT") or "").strip()
        if not commit or commit == "unknown":
            commit = self._git_head_commit()
        branch = str(read_env_var("FILE_MCP_SOURCE_BRANCH") or "").strip()
        if branch == "unknown":
            branch = ""
        build_date = str(read_env_var("FILE_MCP_BUILD_DATE") or "").strip()
        digest = str(read_env_var("FILE_MCP_CONTAINER_DIGEST") or "").strip()
        env_name = str(
            read_env_var("FILE_MCP_UI_ENV") or read_env_var("CLOUD_DOG_ENV") or ""
        ).strip()
        return {
            "source_commit": commit,
            "source_branch": branch,
            "build_date": build_date,
            "container_digest": digest,
            "environment": env_name,
        }

    @staticmethod
    def _git_head_commit() -> str:
        """Best-effort git HEAD for dev/source runs (empty if unavailable)."""
        try:
            import subprocess

            repo_root = path_utils.as_path(
                path_utils.resolve_path(__file__)
            ).parents[2]
            out = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if out.returncode == 0:
                return out.stdout.strip()
        except Exception:
            return ""
        return ""

    def _resolve_login_access_token(self) -> str:
        """Resolve the login bootstrap access token from active profile config."""
        direct = _resolve_auth_api_key_value(
            str(read_env_var("FILE_MCP_API_KEY_PRIMARY") or "").strip()
        )
        if direct:
            return direct

        defaults_path = str(read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or "").strip()
        try:
            cfg = load_config(
                env_path=self.env_file,
                config_path=self.active_config,
                defaults_path=defaults_path or None,
            )
            profile = cfg.profiles.get(self.profile_name)
            if profile is None:
                return ""
            for candidate in profile.auth.api_keys:
                resolved = _resolve_auth_api_key_value(str(candidate))
                if resolved:
                    return resolved
        except Exception:
            return ""
        return ""

    def _build_web_api_proxy(self) -> WebApiProxy | None:
        """Build the standard web→API proxy for the dedicated web role."""
        if self.server_role != "web" or self.config is None:
            return None
        api_server = getattr(self.config, "api_server", None)
        if api_server is None:
            return None
        api_host = str(getattr(api_server, "host", "") or "127.0.0.1").strip()
        if api_host in {"", "0.0.0.0", "::"}:
            api_host = "127.0.0.1"
        api_port = _to_int(getattr(api_server, "port", None), default=8060)

        class _ProxyConfigAdapter:
            def __init__(self, values: dict[str, Any]) -> None:
                self._values = values

            def get(self, key: str, default: Any = None) -> Any:
                return self._values.get(key, default)

        return WebApiProxy.from_config(
            _ProxyConfigAdapter(
                {
                    "web_server.api_base_url": f"http://{api_host}:{api_port}",
                    "api_server.base_url": f"http://{api_host}:{api_port}",
                    "api_server.api_key": "",
                    "api_server.api_key_header": "X-API-Key",
                    "web_server.verify_tls": True,
                    "web_server.proxy_timeout": 180.0,
                }
            )
        )

    @staticmethod
    def _proxy_candidate_headers(headers: dict[str, str]) -> dict[str, str]:
        """Select inbound headers that must be forwarded to the API role."""
        allowed = {
            "accept",
            "authorization",
            "content-type",
            "x-admin-token",
            "x-file-mcp-profile",
            "x-correlation-id",
            "x-request-id",
        }
        return {name: value for name, value in headers.items() if name in allowed and value}

    def _should_proxy_web_request(self, *, path: str, method: str, accept: str) -> bool:
        """Return True when the dedicated web role should proxy to the API role."""
        if self.api_proxy is None:
            return False
        if path in {self.health_path, "/health", "/status", self._ready_path(), self._live_path()}:
            return False
        if path in {"/auth/login", "/auth/me", "/auth/logout"}:
            return False
        admin_identity_prefixes = (
            "/admin/users",
            "/admin/groups",
            "/admin/api-keys",
            "/admin/roles",
        )
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in admin_identity_prefixes):
            return False
        if method in {"GET", "HEAD"} and path.startswith("/admin/"):
            if "text/html" in accept and "application/json" not in accept:
                return False
        return (
            path == "/api"
            or path.startswith("/api/")
            or path == self.mcp_path
            or path.startswith(f"{self.mcp_path.rstrip('/')}/")
            or path == self.web_mcp_path
            or path.startswith(f"{self.web_mcp_path.rstrip('/')}/")
            or path.startswith("/auth/")
            or path.startswith("/admin/")
            or path == "/api/v1/jobs"
            or path.startswith("/api/v1/jobs/")
            or path == "/v1/jobs"
            or path.startswith("/v1/jobs/")
            or path == "/api/v1/logs"
            or path.startswith("/api/v1/logs/")
            or path == "/v1/logs"
            or path.startswith("/v1/logs/")
            or self._is_watches_path(path)
            or path == "/files"
            or path.startswith("/files/")
        )

    async def _send_proxy_response(self, send, *, status: int, data: Any, headers: dict[str, str]) -> None:
        """Write a proxied API response back to the caller."""
        lowered = {str(name).lower(): str(value) for name, value in headers.items()}
        if isinstance(data, bytes):
            body = data
            content_type = lowered.get("content-type", "application/octet-stream")
        elif isinstance(data, str):
            body = data.encode("utf-8")
            content_type = lowered.get("content-type", "text/plain; charset=utf-8")
        else:
            body = json.dumps(data if data is not None else {}).encode("utf-8")
            content_type = lowered.get("content-type", "application/json")
        response_headers = [
            (b"content-type", content_type.encode("utf-8")),
            (b"content-length", str(len(body)).encode("utf-8")),
        ]
        for header_name in ("set-cookie", "location", "cache-control"):
            header_value = lowered.get(header_name, "")
            if header_value:
                response_headers.append(
                    (header_name.encode("utf-8"), header_value.encode("utf-8"))
                )
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    async def _maybe_proxy_web_request(
        self,
        *,
        scope: dict[str, Any],
        receive,
        send,
        headers: dict[str, str],
        path: str,
        method: str,
        accept: str,
    ) -> bool:
        """Proxy web-tier API/auth/MCP routes to the API role."""
        if scope.get("type") != "http" or not self._should_proxy_web_request(
            path=path, method=method, accept=accept
        ):
            return False

        upstream_path = path
        # W28A-258: /webmcp is the browser-facing cookie-auth MCP path.
        # The API server's MCP transport is at /mcp. Rewrite so the proxy
        # forwards to the correct upstream handler.
        if upstream_path == self.web_mcp_path:
            upstream_path = self.mcp_path
        elif upstream_path.startswith(f"{self.web_mcp_path.rstrip('/')}/"):
            upstream_path = f"{self.mcp_path.rstrip('/')}/{upstream_path[len(self.web_mcp_path.rstrip('/')) + 1:]}"
        elif upstream_path == "/api":
            upstream_path = "/"
        elif upstream_path.startswith("/api/") and not (
            upstream_path == "/api/v1/jobs"
            or upstream_path.startswith("/api/v1/jobs/")
            or upstream_path == "/api/v1/logs"
            or upstream_path.startswith("/api/v1/logs/")
        ):
            upstream_path = upstream_path[len("/api") :]

        request_json: Any = None
        if method not in {"GET", "HEAD"}:
            raw_body = await self._read_http_body(receive)
            if raw_body:
                try:
                    request_json = json.loads(raw_body.decode("utf-8"))
                except Exception as exc:
                    await self._send_api_error(
                        send,
                        status=400,
                        code="VALIDATION_ERROR",
                        message=f"invalid JSON body: {exc}",
                    )
                    return True

        query_string = scope.get("query_string", b"")
        params: dict[str, Any] | None = None
        if query_string:
            parsed_query = parse_qs(query_string.decode("utf-8"))
            params = {
                key: values[0] if len(values) == 1 else values
                for key, values in parsed_query.items()
            }

        cookies = dict(HTTPConnection(scope).cookies)
        proxy_headers = self._proxy_candidate_headers(headers)
        cookie_api_path = (
            path == "/api/v1/jobs"
            or path.startswith("/api/v1/jobs/")
            or path == "/v1/jobs"
            or path.startswith("/v1/jobs/")
            or path == "/api/v1/logs"
            or path.startswith("/api/v1/logs/")
            or path == "/v1/logs"
            or path.startswith("/v1/logs/")
            or self._is_watches_path(path)
            # The SPA loads storage profiles from this canonical admin API
            # after cookie login.  The API role cannot validate the web role's
            # in-memory session, so carry its authenticated proxy credentials.
            or path == "/admin/profiles"
            or path.startswith("/admin/profiles/")
            or path == "/api/admin/profiles"
            or path.startswith("/api/admin/profiles/")
        )
        if (
            path == self.web_mcp_path
            or path.startswith(f"{self.web_mcp_path.rstrip('/')}/")
            or cookie_api_path
        ):
            session_is_valid = self._get_session_from_cookie(headers) is not None
            if not session_is_valid and cookies.get(self._cookie_name):
                probe_response = await self.api_proxy.request(
                    "GET",
                    "/auth/me",
                    headers=self._proxy_candidate_headers(headers),
                    cookies=cookies,
                )
                session_is_valid = probe_response.ok
            if (
                session_is_valid
                and self._login_access_token
                and not proxy_headers.get("authorization")
            ):
                proxy_headers["authorization"] = f"Bearer {self._login_access_token}"
            session = self._get_session_from_cookie(headers)
            if (
                session is not None
                and session.get("role") == "admin"
                and self.admin_ui_token
            ):
                # The API role cannot read the web role's in-memory session.
                # Forward the existing internal admin credential only after the
                # web role has validated the HttpOnly session cookie.
                proxy_headers["x-admin-token"] = self.admin_ui_token
        response = await self.api_proxy.request(
            method,
            upstream_path,
            json=request_json,
            params=params,
            headers=proxy_headers,
            cookies=cookies or None,
        )
        await self._send_proxy_response(
            send,
            status=response.status_code,
            data=response.data if response.data is not None else {"error": response.error or "proxy error"},
            headers=response.headers,
        )
        return True

    def _ready_path(self) -> str:
        """Handle ready path."""
        base = self.health_path.rsplit("/", 1)[0] if "/" in self.health_path else ""
        if not base:
            return "/ready"
        return f"{base}/ready"

    def _live_path(self) -> str:
        """Handle live path."""
        base = self.health_path.rsplit("/", 1)[0] if "/" in self.health_path else ""
        if not base:
            return "/live"
        return f"{base}/live"

    @staticmethod
    def _legacy_api_alias(path: str) -> str | None:
        """Handle legacy api alias."""
        if path == "/app/v1":
            return "/api/v1"
        if path.startswith("/app/v1/"):
            return "/api/v1/" + path[len("/app/v1/") :]
        return None

    @staticmethod
    def _legacy_root_alias(path: str) -> str | None:
        """Handle legacy root alias."""
        if path == "/app/v1":
            return "/"
        if path.startswith("/app/v1/"):
            return "/" + path[len("/app/v1/") :]
        return None

    def _dependency_checks(self) -> tuple[str, dict[str, Any]]:
        """Handle dependency checks."""
        states = ENDPOINT_HEALTH_MANAGER.get_profile_states(self.profile_name)
        checks: dict[str, Any] = {}
        all_ok = True
        for backend, state in sorted(states.items()):
            checks[backend] = {
                "status": state.status,
                "reason": state.reason,
                "requires_restart": state.requires_restart,
            }
            if state.status != "healthy":
                all_ok = False
        db_status = database_health(self.db_runtime)
        checks["database"] = {
            "status": "healthy" if db_status.get("ok") else "error",
            "details": db_status,
        }
        if not db_status.get("ok"):
            all_ok = False
        return ("ok" if all_ok else "degraded"), checks

    def _resolve_status_roots(self) -> list[Path]:
        """Resolve scope roots used to derive status service metrics."""
        defaults_path = str(read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or "").strip()
        try:
            cfg = load_config(
                env_path=self.env_file,
                config_path=self.active_config,
                defaults_path=defaults_path or None,
            )
            profile = cfg.profiles.get(self.profile_name)
            if profile is None:
                return []
            roots: list[Path] = []
            for raw_root in profile.scope.roots:
                expanded = path_utils.expand_user(str(raw_root))
                if not path_utils.is_absolute(expanded):
                    expanded = path_utils.resolve_path(
                        path_utils.join(path_utils.cwd(), expanded)
                    )
                roots.append(path_utils.as_path(expanded))
            return roots
        except Exception:
            return []

    @staticmethod
    def _read_total_memory_bytes() -> int | None:
        """Read host total memory from /proc/meminfo when available."""
        try:
            for line in path_utils.read_text("/proc/meminfo").splitlines():
                if not line.startswith("MemTotal:"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                return int(parts[1]) * 1024
        except Exception:
            return None
        return None

    @staticmethod
    def _read_rss_bytes() -> int | None:
        """Read process RSS in bytes."""
        try:
            parts = path_utils.read_text("/proc/self/statm").split()
            if len(parts) >= 2:
                pages = int(parts[1])
                page_size = os.sysconf("SC_PAGE_SIZE")
                return pages * page_size
        except Exception:
            pass
        try:
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Linux reports KiB, macOS reports bytes.
            if rss <= 0:
                return None
            if rss < 1_000_000_000:
                return int(rss * 1024)
            return int(rss)
        except Exception:
            return None

    def _sample_cpu_percent(self) -> float:
        """Sample process CPU usage as a percentage."""
        wall_now = time.monotonic()
        proc_now = time.process_time()
        wall_delta = wall_now - self._cpu_last_wall
        proc_delta = proc_now - self._cpu_last_process
        self._cpu_last_wall = wall_now
        self._cpu_last_process = proc_now
        if wall_delta <= 0:
            return 0.0
        cpu_count = max(1, os.cpu_count() or 1)
        return max(0.0, min(100.0, (proc_delta / wall_delta) * (100.0 / cpu_count)))

    def _read_disk_percent(self) -> float | None:
        """Read disk utilisation percentage for the first configured scope root."""
        roots = self._status_roots
        probe_path_str: str | None = None
        for root in roots:
            if path_utils.exists(str(root)):
                probe_path_str = str(root)
                break
        if probe_path_str is None:
            probe_path_str = path_utils.cwd()
        try:
            total, used, _free = path_utils.disk_usage(probe_path_str)
            if total <= 0:
                return None
            return (used / total) * 100.0
        except Exception:
            return None

    @staticmethod
    def _count_open_socket_fds() -> int:
        """Approximate active connections by counting open socket file descriptors."""
        try:
            total = 0
            for entry in path_utils.iter_dir("/proc/self/fd"):
                try:
                    target = path_utils.read_link(entry)
                except OSError:
                    continue
                if target.startswith("socket:["):
                    total += 1
            return total
        except Exception:
            return 0

    def _compute_service_metrics(self) -> dict[str, Any]:
        """Compute file/profile service metrics for /status payload."""
        now = time.monotonic()
        cached = self._service_metrics_cache
        if cached is not None and (now - cached[0]) < 15.0:
            return cached[1]

        roots = self._status_roots
        max_files = _to_int(read_env_var("FILE_MCP_STATUS_MAX_FILES"), default=50_000)
        file_count = 0
        total_bytes = 0
        for root in roots:
            if file_count >= max_files:
                break
            if not path_utils.exists(str(root)):
                continue
            for current_root, _dirs, files in path_utils.walk(str(root)):
                for filename in files:
                    if file_count >= max_files:
                        break
                    candidate = path_utils.join(current_root, filename)
                    try:
                        stat = path_utils.file_stat(candidate)
                    except OSError:
                        continue
                    if not path_utils.is_file(candidate):
                        continue
                    file_count += 1
                    total_bytes += int(stat.st_size)
                if file_count >= max_files:
                    break

        payload = {
            "file_count": file_count,
            "profile_count": len(self.profile_names) or 1,
            "storage_used_mb": round(total_bytes / (1024 * 1024), 2),
        }
        self._service_metrics_cache = (now, payload)
        return payload

    def _status_payload(self) -> dict[str, Any]:
        """Build /status payload with runtime resource metrics."""
        uptime_seconds = int(max(0, time.time() - self._started_at))
        rss_bytes = self._read_rss_bytes()
        total_memory = self._read_total_memory_bytes()
        memory_mb = (
            round((rss_bytes or 0) / (1024 * 1024), 2) if rss_bytes is not None else None
        )
        memory_percent = (
            round((rss_bytes / total_memory) * 100.0, 2)
            if (rss_bytes is not None and total_memory and total_memory > 0)
            else None
        )
        disk_percent = self._read_disk_percent()
        return {
            "uptime_seconds": uptime_seconds,
            "uptime": uptime_seconds,
            "memory_mb": memory_mb,
            "memory_percent": memory_percent,
            "cpu_percent": round(self._sample_cpu_percent(), 2),
            "disk_percent": round(disk_percent, 2) if disk_percent is not None else None,
            "active_connections": self._count_open_socket_fds(),
            "service_metrics": self._compute_service_metrics(),
        }

    def _health_response_payload(self) -> dict[str, Any]:
        """Build the JSON payload used by the health endpoint and settings UI."""
        readiness, checks = self._dependency_checks()
        return {
            "status": "ok",
            "checks": checks,
            "version": self.version,
            "service": "file-mcp-server",
            "application": {"name": self.app_name},
            "runtime": {"env_file": self.env_file},
            "profile": self.profile_name,
            "transport": self.transport,
            "readiness": readiness,
        }

    def _list_tools_payload(self) -> dict[str, Any]:
        """Handle list tools payload."""
        if not callable(self.registry_provider):
            return {"tools": []}
        registry = self.registry_provider()
        tools = [_tool_payload(tool) for tool in registry.list_tools()]
        return {"tools": tools}

    @staticmethod
    def _rest_file_id(path: str) -> str:
        """Return a URL-safe lifecycle id for a scoped file path."""
        raw = str(path or "").encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _rest_file_path_from_id(file_id: str) -> str:
        """Decode a URL-safe lifecycle id back to the scoped file path."""
        value = str(file_id or "").strip()
        if not value:
            raise ValueError("file id is required")
        padding = "=" * (-len(value) % 4)
        try:
            return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode(
                "utf-8"
            )
        except Exception as exc:
            raise ValueError("invalid file id") from exc

    @staticmethod
    def _rest_file_scope_allows(
        *, required: str, scopes: set[str], profile_name: str
    ) -> bool:
        """Return whether API-key scopes allow the REST file operation."""
        if "*" in scopes or "admin" in scopes or "admin:*" in scopes:
            return True
        if required in scopes:
            return True
        profile_tokens = {
            "profile:*",
            f"profile:{profile_name}",
            f"profile:{profile_name}:write",
        }
        if required == "files.write":
            return bool(
                {
                    "files.write",
                    "file:write",
                    "file:*",
                    "profile:write",
                }
                & scopes
                or profile_tokens & scopes
            )
        return bool(
            {
                "files.read",
                "files.write",
                "files.list",
                "files.search",
                "file:read",
                "file:list",
                "file:search",
                "file:write",
                "file:*",
                "profile:read",
                "profile:write",
            }
            & scopes
            or profile_tokens & scopes
            or f"profile:{profile_name}:read" in scopes
        )

    def _rest_file_registry(self, profile_name: str) -> ToolRegistry:
        """Resolve the existing tool registry for a REST-selected profile."""
        if not callable(self.registry_provider):
            raise AdminIdentityError(
                "INTERNAL_ERROR", "tool registry unavailable", status=500
            )
        try:
            return self.registry_provider(profile_name)
        except TypeError:
            return self.registry_provider()

    @staticmethod
    def _rest_file_entry(path: str, *, profile_name: str, **extra: Any) -> dict[str, Any]:
        """Build the common REST file metadata shape."""
        payload = {
            "id": HealthCheckMiddleware._rest_file_id(path),
            "path": path,
            "name": path.rsplit("/", 1)[-1] if path else "",
            "profile": profile_name,
        }
        payload.update({key: value for key, value in extra.items() if value is not None})
        return payload

    # req: FR-012 FR-016 FR-017
    async def _handle_rest_file_lifecycle(
        self,
        *,
        scope: dict[str, Any],
        receive,
        send,
        headers: dict[str, str],
        path: str,
        method: str,
    ) -> bool:
        """Serve the PS-78 REST file lifecycle contract through file tools."""
        if path != "/files" and not path.startswith("/files/"):
            return False

        tail = path[len("/files") :].strip("/")
        route: str
        file_id: str | None = None
        required = "files.read"
        if tail == "":
            if method != "GET":
                return False
            route = "list"
        elif tail == "upload":
            if method != "POST":
                return False
            route = "upload"
            required = "files.write"
        elif tail == "upload_base64":
            if method != "POST":
                return False
            route = "upload_base64"
            required = "files.write"
        elif tail.endswith("/download"):
            if method != "GET":
                return False
            route = "download"
            file_id = tail[: -len("/download")].strip("/")
        else:
            if "/" in tail or method not in {"GET", "DELETE"}:
                return False
            route = "metadata" if method == "GET" else "delete"
            file_id = tail
            if method == "DELETE":
                required = "files.write"

        try:
            auth_info, selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            scopes = self._token_scopes(auth_info)
            if auth_info is None:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return True
            if not self._rest_file_scope_allows(
                required=required, scopes=scopes, profile_name=selected_profile
            ):
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message=f"Missing permission: {required}",
                )
                return True

            registry = self._rest_file_registry(selected_profile)
            query = parse_qs(scope.get("query_string", b"").decode("utf-8"))

            if route == "list":
                list_path = str((query.get("path") or ["."])[0] or ".")
                recursive = str((query.get("recursive") or ["false"])[0]).lower() in {
                    "1",
                    "true",
                    "yes",
                }
                listed = registry.get("list_dir").handler(
                    path=list_path, recursive=recursive
                )
                items = []
                for entry in listed.get("entry_details", []):
                    entry_path = str(entry.get("path") or "")
                    item = self._rest_file_entry(
                        entry_path,
                        profile_name=selected_profile,
                        is_dir=bool(entry.get("is_dir")),
                        size=entry.get("size"),
                        modified_at=entry.get("modified_at"),
                        created_at=entry.get("created_at"),
                    )
                    items.append(item)
                await self._send_json(
                    send,
                    status=200,
                    payload={
                        "ok": True,
                        "profile": selected_profile,
                        "path": listed.get("path", list_path),
                        "items": items,
                    },
                )
                return True

            if route in {"upload", "upload_base64"}:
                payload = await self._read_json_body(receive)
                target_path = str(payload.get("path") or "").strip()
                if not target_path:
                    raise AdminIdentityError(
                        "VALIDATION_ERROR", "path is required", status=422
                    )
                overwrite = bool(payload.get("overwrite", True))
                if route == "upload_base64":
                    data = str(payload.get("data") or "")
                    result = registry.get("b64_decode_to_file").handler(
                        path=target_path,
                        data=data,
                        urlsafe=bool(payload.get("urlsafe", False)),
                        overwrite=overwrite,
                    )
                    bytes_written = result.get("bytes_written")
                else:
                    if "content" not in payload:
                        raise AdminIdentityError(
                            "VALIDATION_ERROR", "content is required", status=422
                        )
                    content = str(payload.get("content") or "")
                    result = registry.get("write_file").handler(
                        path=target_path,
                        content=content,
                        encoding=str(payload.get("encoding") or "utf-8"),
                        overwrite=overwrite,
                    )
                    bytes_written = len(content.encode(str(payload.get("encoding") or "utf-8")))
                stored_path = str(result.get("path") or target_path)
                await self._send_json(
                    send,
                    status=201,
                    payload={
                        "ok": True,
                        "file": self._rest_file_entry(
                            stored_path,
                            profile_name=selected_profile,
                            size=bytes_written,
                        ),
                    },
                )
                return True

            if file_id is None:
                raise AdminIdentityError("VALIDATION_ERROR", "file id is required")
            target_path = self._rest_file_path_from_id(file_id)

            if route == "metadata":
                encoded = registry.get("b64_encode_file").handler(path=target_path)
                raw = b64_decode(str(encoded.get("data") or ""))
                await self._send_json(
                    send,
                    status=200,
                    payload={
                        "ok": True,
                        "file": self._rest_file_entry(
                            target_path,
                            profile_name=selected_profile,
                            size=len(raw),
                        ),
                    },
                )
                return True

            if route == "download":
                encoded = registry.get("b64_encode_file").handler(path=target_path)
                await self._send_json(
                    send,
                    status=200,
                    payload={
                        "ok": True,
                        "file": self._rest_file_entry(
                            target_path, profile_name=selected_profile
                        ),
                        "encoding": "base64",
                        "data": encoded.get("data", ""),
                    },
                )
                return True

            if route == "delete":
                result = registry.get("delete_file").handler(
                    path=target_path, missing_ok=False
                )
                await self._send_json(
                    send,
                    status=200,
                    payload={
                        "ok": True,
                        "deleted": True,
                        "file": self._rest_file_entry(
                            str(result.get("path") or target_path),
                            profile_name=selected_profile,
                        ),
                    },
                )
                return True

        except AdminIdentityError as exc:
            await self._send_api_error(
                send, status=exc.status, code=exc.code, message=str(exc)
            )
            return True
        except FileNotFoundError:
            await self._send_api_error(
                send, status=404, code="NOT_FOUND", message="file not found"
            )
            return True
        except PermissionError as exc:
            await self._send_api_error(
                send, status=403, code="FORBIDDEN", message=str(exc)
            )
            return True
        except ValueError as exc:
            await self._send_api_error(
                send, status=422, code="VALIDATION_ERROR", message=str(exc)
            )
            return True
        except Exception as exc:
            message = str(exc)
            if "no such file" in message.lower() or "not found" in message.lower():
                await self._send_api_error(
                    send, status=404, code="NOT_FOUND", message="file not found"
                )
                return True
            await self._send_api_error(
                send, status=500, code="INTERNAL_ERROR", message=message
            )
            return True

        return False

    def _w28a742_session_manager(self):
        """Return the file-mcp DB session manager, or ``None`` when absent.

        The chokepoint (``guard.check_route_guard``) and the inline
        ``/idam/v1/rbac/bindings`` handlers BOTH use this to open a fresh
        per-request session for the ``RBACBindingRepository``. Returning
        ``None`` causes the chokepoint to fail-open to the existing
        dispatch — appropriate for bootstrap/test scenarios where the DB
        runtime is not yet initialised.
        """
        if self.db_runtime is None:
            return None
        return getattr(self.db_runtime, "session_manager", None)

    def _w28a742_get_engine(self):
        """Lazily construct + cache the shared :class:`RBACEngine`.

        The default ctor composes the W28A-741 6-baseline role+permission
        catalog automatically; no per-service overlay is required for the
        chokepoint or the binding write API.
        """
        if self._w28a742_engine is None:
            try:
                from cloud_dog_idam import RBACEngine
                self._w28a742_engine = RBACEngine()
            except Exception:
                return None
        return self._w28a742_engine

    def _w28a742_get_membership(self):
        """Lazily construct + cache the :class:`FileMcpMembershipResolver`."""
        if self._w28a742_membership is None:
            session_manager = self._w28a742_session_manager()
            if session_manager is None:
                return None
            try:
                from .idam_seam import FileMcpMembershipResolver
                self._w28a742_membership = FileMcpMembershipResolver(
                    session_manager=session_manager
                )
            except Exception:
                return None
        return self._w28a742_membership

    async def _w28a742_handle_rbac_bindings(
        self,
        *,
        scope,
        receive,
        send,
        method: str,
        idam_sub: str,
        headers: dict[str, str],
    ) -> bool:
        """DB-backed ``/idam/v1/rbac/bindings`` handlers (W28A-742 §3.3).

        Returns ``True`` when the request was served, ``False`` to fall
        through to the existing dispatch.
        """
        session_manager = self._w28a742_session_manager()
        if session_manager is None:
            return False
        try:
            from cloud_dog_idam.storage.sqlalchemy.models import RBACBindingORM
            from cloud_dog_idam.storage.sqlalchemy.repositories import (
                RBACBindingRepository,
            )
        except Exception:
            return False

        # Determine binding id from sub-path. Both 'rbac/bindings' and
        # 'rbac-bindings' aliases are stripped; trailing segment is the id.
        if idam_sub.startswith("rbac/bindings"):
            _trim = idam_sub[len("rbac/bindings"):]
        else:
            _trim = idam_sub[len("rbac-bindings"):]
        _trim = _trim.strip("/")
        binding_id: str | None = _trim or None

        from .guard import (
            _resolve_principal_lightweight,
            _principal_has_wildcard,
        )

        principal = _resolve_principal_lightweight(self, scope, headers)
        if principal is None:
            await self._send_bytes(
                send,
                status=401,
                body=b'{"ok":false,"error":{"code":"UNAUTHENTICATED"}}',
                content_type="application/json",
            )
            return True
        is_admin = _principal_has_wildcard(principal)

        def _row_to_dict(row) -> dict:
            binding_id = row.binding_id
            subject_id = row.subject_id
            resource_id = row.resource_id
            created_at = row.created_at.isoformat() if row.created_at is not None else None
            return {
                "id": binding_id,
                "binding_id": binding_id,
                "subject_type": row.subject_type,
                "subject": subject_id,
                "subject_id": subject_id,
                "project": row.project,
                "resource_type": row.resource_type,
                "resource": resource_id,
                "resource_id": resource_id,
                "permission": row.permission,
                "granted_by": row.granted_by,
                "granted_at": created_at,
                "created_at": created_at,
            }

        # GET (list) — idam.rbac.read
        if method == "GET" and binding_id is None:
            try:
                with session_manager.session() as session:
                    repo = RBACBindingRepository(session)
                    if is_admin:
                        try:
                            from cloud_dog_idam.storage.sqlalchemy.repositories import (
                                PaginationParams,
                            )
                            page = repo.list(PaginationParams(page=1, page_size=200))
                            rows = list(getattr(page, "items", page))
                        except Exception:
                            rows = []
                    else:
                        rows = list(repo.by_subject("user", principal["user_id"]))
                        membership = self._w28a742_get_membership()
                        if membership is not None:
                            try:
                                gids = membership.groups_of(principal["user_id"])
                            except Exception:
                                gids = set()
                            for gid in gids:
                                rows.extend(repo.by_subject("group", gid))
                    body = json.dumps([_row_to_dict(r) for r in rows]).encode("utf-8")
                await self._send_bytes(
                    send, status=200, body=body, content_type="application/json"
                )
                return True
            except Exception:
                await self._send_bytes(
                    send,
                    status=500,
                    body=b'{"ok":false,"error":{"code":"INTERNAL"}}',
                    content_type="application/json",
                )
                return True

        # POST (create) — idam.rbac.write (admin)
        if method == "POST" and binding_id is None:
            if not is_admin:
                await self._send_bytes(
                    send,
                    status=403,
                    body=b'{"ok":false,"error":{"code":"FORBIDDEN"}}',
                    content_type="application/json",
                )
                return True
            try:
                body_bytes = await self._read_http_body(receive)
                payload = json.loads(body_bytes or b"{}")
            except Exception:
                await self._send_bytes(
                    send,
                    status=400,
                    body=b'{"ok":false,"error":{"code":"BAD_REQUEST"}}',
                    content_type="application/json",
                )
                return True
            try:
                import uuid as _uuid
                from datetime import datetime as _dt, timezone as _tz

                subject_id = str(
                    payload.get("subject_id") or payload.get("subject") or ""
                ).strip()
                resource_id = str(
                    payload.get("resource_id") or payload.get("resource") or "*"
                ).strip()
                binding = RBACBindingORM(
                    binding_id=str(payload.get("binding_id") or _uuid.uuid4()),
                    subject_type=str(payload.get("subject_type") or ""),
                    subject_id=subject_id,
                    project=str(payload.get("project") or "platform"),
                    resource_type=str(payload.get("resource_type") or ""),
                    resource_id=resource_id or "*",
                    permission=str(payload.get("permission") or ""),
                    granted_by=str(principal["user_id"]),
                    created_at=_dt.now(_tz.utc),
                )
                with session_manager.session() as session:
                    repo = RBACBindingRepository(session)
                    saved = repo.save(binding)
                    session.commit()
                    body = json.dumps(_row_to_dict(saved)).encode("utf-8")
                engine = self._w28a742_get_engine()
                inv = getattr(engine, "_invalidate_user", None)
                if callable(inv):
                    try:
                        inv(binding.subject_id)
                    except Exception:
                        pass
                await self._send_bytes(
                    send, status=201, body=body, content_type="application/json"
                )
                return True
            except Exception:
                await self._send_bytes(
                    send,
                    status=500,
                    body=b'{"ok":false,"error":{"code":"INTERNAL"}}',
                    content_type="application/json",
                )
                return True

        # PUT/PATCH — idam.rbac.write (admin)
        if method in ("PUT", "PATCH") and binding_id is not None:
            if not is_admin:
                await self._send_bytes(
                    send,
                    status=403,
                    body=b'{"ok":false,"error":{"code":"FORBIDDEN"}}',
                    content_type="application/json",
                )
                return True
            try:
                body_bytes = await self._read_http_body(receive)
                payload = json.loads(body_bytes or b"{}")
            except Exception:
                await self._send_bytes(
                    send,
                    status=400,
                    body=b'{"ok":false,"error":{"code":"BAD_REQUEST"}}',
                    content_type="application/json",
                )
                return True
            try:
                with session_manager.session() as session:
                    repo = RBACBindingRepository(session)
                    row = repo.get_by_id(binding_id)
                    if row is None:
                        await self._send_bytes(
                            send,
                            status=404,
                            body=b'{"ok":false,"error":{"code":"NOT_FOUND"}}',
                            content_type="application/json",
                        )
                        return True
                    if "permission" in payload:
                        row.permission = str(payload.get("permission") or "")
                    session.commit()
                    body = json.dumps(_row_to_dict(row)).encode("utf-8")
                    subject_id = row.subject_id
                engine = self._w28a742_get_engine()
                inv = getattr(engine, "_invalidate_user", None)
                if callable(inv):
                    try:
                        inv(subject_id)
                    except Exception:
                        pass
                await self._send_bytes(
                    send, status=200, body=body, content_type="application/json"
                )
                return True
            except Exception:
                await self._send_bytes(
                    send,
                    status=500,
                    body=b'{"ok":false,"error":{"code":"INTERNAL"}}',
                    content_type="application/json",
                )
                return True

        # GET (by id) — idam.rbac.read
        if method == "GET" and binding_id is not None:
            try:
                with session_manager.session() as session:
                    repo = RBACBindingRepository(session)
                    row = repo.get_by_id(binding_id)
                if row is None:
                    await self._send_bytes(
                        send,
                        status=404,
                        body=b'{"ok":false,"error":{"code":"NOT_FOUND"}}',
                        content_type="application/json",
                    )
                    return True
                if not is_admin:
                    own = (
                        getattr(row, "subject_type", "") == "user"
                        and getattr(row, "subject_id", None) == principal["user_id"]
                    )
                    group_owned = False
                    if not own and getattr(row, "subject_type", "") == "group":
                        membership = self._w28a742_get_membership()
                        if membership is not None:
                            try:
                                group_owned = getattr(row, "subject_id", None) in (
                                    membership.groups_of(principal["user_id"])
                                )
                            except Exception:
                                group_owned = False
                    if not (own or group_owned):
                        await self._send_bytes(
                            send,
                            status=403,
                            body=b'{"ok":false,"error":{"code":"FORBIDDEN"}}',
                            content_type="application/json",
                        )
                        return True
                body = json.dumps(_row_to_dict(row)).encode("utf-8")
                await self._send_bytes(
                    send, status=200, body=body, content_type="application/json"
                )
                return True
            except Exception:
                await self._send_bytes(
                    send,
                    status=500,
                    body=b'{"ok":false,"error":{"code":"INTERNAL"}}',
                    content_type="application/json",
                )
                return True

        # DELETE — idam.rbac.write (admin)
        if method == "DELETE" and binding_id is not None:
            if not is_admin:
                await self._send_bytes(
                    send,
                    status=403,
                    body=b'{"ok":false,"error":{"code":"FORBIDDEN"}}',
                    content_type="application/json",
                )
                return True
            try:
                subject_id = None
                with session_manager.session() as session:
                    repo = RBACBindingRepository(session)
                    row = repo.get_by_id(binding_id)
                    if row is not None:
                        subject_id = row.subject_id
                    ok = repo.delete(binding_id, soft=False)
                    session.commit()
                if not ok:
                    await self._send_bytes(
                        send,
                        status=404,
                        body=b'{"ok":false,"error":{"code":"NOT_FOUND"}}',
                        content_type="application/json",
                    )
                    return True
                engine = self._w28a742_get_engine()
                inv = getattr(engine, "_invalidate_user", None)
                if callable(inv) and subject_id is not None:
                    try:
                        inv(subject_id)
                    except Exception:
                        pass
                await self._send_bytes(
                    send,
                    status=204,
                    body=b"",
                    content_type="application/json",
                )
                return True
            except Exception:
                await self._send_bytes(
                    send,
                    status=500,
                    body=b'{"ok":false,"error":{"code":"INTERNAL"}}',
                    content_type="application/json",
                )
                return True

        return False

    def _get_session_from_cookie(self, headers: dict[str, str]) -> dict | None:
        """Extract and validate session from cookie header."""
        import time as _time
        cookie_header = headers.get("cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{self._cookie_name}="):
                token = part[len(self._cookie_name) + 1:]
                sess = self._sessions.get(token)
                if sess and _time.time() - sess.get("_created", 0) < 3600:
                    return sess
                self._sessions.pop(token, None)
        # W28E-1837 SECURITY FIX: a request whose cookie does not match a stored,
        # unexpired session is ANONYMOUS. The previous "cookie session fallback"
        # (which returned the most-recent active session to ANY cookieless caller
        # whenever auth_mode defaulted to "cookie") leaked the last-authenticated
        # principal — e.g. /auth/me returned an admin principal to an anonymous
        # caller after any admin login. Per route_guards.py and PS-82 §3.1, an
        # unauthenticated caller MUST resolve to None (-> 401 / {user:null}); a
        # session is only ever returned when the caller presents its own valid
        # session cookie token (matched above). No global-session fallback.
        return None

    async def _handle_auth_login(self, receive, send, headers: dict[str, str]) -> bool:
        """Handle POST /auth/login — validate credentials, set session cookie."""
        import time as _time
        body = await self._read_http_body(receive)
        try:
            data = json.loads(body)
        except Exception:
            await self._send_bytes(send, status=400, body=b'{"detail":"Invalid JSON"}', content_type="application/json")
            return True
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()
        if not username or not password:
            await self._send_bytes(send, status=400, body=b'{"detail":"Username and password required"}', content_type="application/json")
            return True
        # Thread-a flat-role credential check (W28A-728-R4). Compare against
        # EVERY account with secrets.compare_digest so a wrong username and a
        # wrong password are indistinguishable (no username enumeration). The
        # matched account decides the flat role; permissions come from the ONE
        # shared idam guard via the flat role catalog (no fork).
        matched_role: str | None = None
        for cand_user, (cand_pw, cand_role) in self._flat_accounts.items():
            user_ok = secrets.compare_digest(username, cand_user)
            pw_ok = secrets.compare_digest(password, cand_pw)
            if user_ok and pw_ok:
                matched_role = cand_role
                break
        if matched_role is None:
            await self._send_bytes(send, status=401, body=b'{"detail":"Invalid credentials"}', content_type="application/json")
            return True
        flat_role = normalise_flat_role(matched_role)
        permissions = permissions_for_role(flat_role)
        user_id = {
            FLAT_ADMIN_ROLE: "1",
            FLAT_READ_WRITE_ROLE: "2",
            FLAT_READ_ONLY_ROLE: "3",
        }[flat_role]
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {
            "user": username,
            "user_id": user_id,
            "role": flat_role,
            "permissions": permissions,
            "_created": _time.time(),
        }
        response_payload = {
            "user": {
                "id": user_id,
                "displayName": username,
                "email": None,
                "roles": [flat_role],
                "permissions": list(permissions),
            }
        }
        if self._login_access_token:
            response_payload["access_token"] = self._login_access_token
            response_payload["expires_in"] = 3600
        resp_body = json.dumps(response_payload).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(resp_body)).encode()),
                (b"set-cookie", f"{self._cookie_name}={token}; HttpOnly; SameSite=Lax; Max-Age=3600; Path=/".encode()),
            ],
        })
        await send({"type": "http.response.body", "body": resp_body})
        return True

    @staticmethod
    def _token_roles(auth_info: Any | None) -> list[str]:
        """Extract role names from token/auth metadata."""
        if auth_info is None:
            return []
        roles: set[str] = set()
        raw_roles = getattr(auth_info, "roles", None) or []
        for value in raw_roles:
            text = str(value).strip()
            if text:
                roles.add(text)
        claims = getattr(auth_info, "claims", None)
        if isinstance(claims, dict):
            claim_roles = claims.get("roles")
            if isinstance(claim_roles, list):
                for value in claim_roles:
                    text = str(value).strip()
                    if text:
                        roles.add(text)
            claim_role = claims.get("role")
            if claim_role is not None:
                text = str(claim_role).strip()
                if text:
                    roles.add(text)
        return sorted(roles)

    def _auth_user_payload(self, auth_info: Any) -> dict[str, Any]:
        """Build a stable /auth/me payload for bearer-authenticated sessions."""
        claims = getattr(auth_info, "claims", None)
        claim_map = claims if isinstance(claims, dict) else {}
        permissions = sorted(self._token_scopes(auth_info))
        raw_claim_permissions = claim_map.get("permissions")
        if isinstance(raw_claim_permissions, list):
            for value in raw_claim_permissions:
                text = str(value).strip()
                if text and text not in permissions:
                    permissions.append(text)

        user_id = ""
        for attribute in ("subject", "sub", "identity", "principal", "user_id", "client_id"):
            value = getattr(auth_info, attribute, None)
            if value is None and claim_map:
                value = claim_map.get(attribute)
            text = str(value or "").strip()
            if text:
                user_id = text
                break
        if not user_id:
            user_id = "api-key-user"

        display_name = (
            str(claim_map.get("display_name") or "").strip()
            or str(claim_map.get("username") or "").strip()
            or user_id
        )
        email = str(claim_map.get("email") or "").strip() or None
        return {
            "id": user_id,
            "displayName": display_name,
            "email": email,
            "roles": self._token_roles(auth_info),
            "permissions": permissions,
        }

    async def _handle_auth_me(self, send, headers: dict[str, str], scope: dict[str, Any]) -> bool:
        """Handle GET /auth/me — return current session user."""
        sess = self._get_session_from_cookie(headers)
        if sess:
            # Thread-a (W28A-728-R4): echo the session's own flat role +
            # shared-guard-derived permissions, NOT a hardcoded admin/"*". A
            # read-only session must report a view-only permission set so the UI
            # gates its write affordances correctly (and is never silently admin).
            role = normalise_flat_role(sess.get("role"))
            permissions = sess.get("permissions")
            if not isinstance(permissions, list):
                permissions = permissions_for_role(role)
            resp_body = json.dumps({"user": {"id": sess["user_id"], "displayName": sess["user"], "email": None, "roles": [role], "permissions": list(permissions)}}).encode("utf-8")
            await self._send_bytes(
                send,
                status=200,
                body=resp_body,
                content_type="application/json",
                close=True,
            )
            return True

        auth_info, _selected_profile = await self._authenticate_request(
            scope=scope, headers=headers
        )
        if auth_info is None:
            query = parse_qs(
                (scope.get("query_string") or b"").decode("utf-8", errors="ignore")
            )
            optional = str((query.get("optional") or [""])[0]).lower() in {
                "1",
                "true",
                "yes",
            }
            if optional:
                await self._send_json(
                    send,
                    status=200,
                    payload={"user": None, "authenticated": False},
                )
                return True
            await self._send_bytes(send, status=401, body=b'{"detail":"Not authenticated"}', content_type="application/json")
            return True

        resp_body = json.dumps({"user": self._auth_user_payload(auth_info)}).encode("utf-8")
        await self._send_bytes(
            send,
            status=200,
            body=resp_body,
            content_type="application/json",
            close=True,
        )
        return True

    async def _handle_auth_status(self, send, headers: dict[str, str], scope: dict[str, Any]) -> bool:
        """Handle GET /auth/status — best-effort capability probe for the IDAM WebUI.

        W28A-889-A-R2: returns the caller's real capability so the shared @cloud-dog/idam
        Users/Groups/API-Keys/Roles/RBAC pages can gate admin affordances without a 404 (which
        the deployed Users page surfaced as a "Not Found" banner). Auth-safe: reflects only the
        caller's own identity; an unauthenticated caller is denied (401), never handed admin.
        """
        sess = self._get_session_from_cookie(headers)
        if sess:
            # Thread-a (W28A-728-R4): reflect the caller's own flat-role
            # capability. Only the admin flat role is a system admin; read-write
            # and read-only report their real shared-guard permission set (never
            # escalated to admin).
            role = normalise_flat_role(sess.get("role"))
            is_admin = role_is_admin(role)
            permissions = sess.get("permissions")
            if not isinstance(permissions, list):
                permissions = permissions_for_role(role)
            resp_body = json.dumps({
                "authenticated": True,
                "username": sess["user"],
                "is_system_admin": is_admin,
                "permissions": list(permissions),
            }).encode("utf-8")
            await self._send_bytes(send, status=200, body=resp_body, content_type="application/json")
            return True

        auth_info, _selected_profile = await self._authenticate_request(scope=scope, headers=headers)
        if auth_info is None:
            await self._send_bytes(send, status=401, body=b'{"detail":"Not authenticated"}', content_type="application/json")
            return True

        payload = self._auth_user_payload(auth_info)
        permissions = payload.get("permissions") or []
        is_admin = "admin" in (payload.get("roles") or []) or "*" in permissions
        resp_body = json.dumps({
            "authenticated": True,
            "username": payload.get("displayName") or payload.get("id"),
            "is_system_admin": is_admin,
            "permissions": permissions,
        }).encode("utf-8")
        await self._send_bytes(send, status=200, body=resp_body, content_type="application/json")
        return True

    async def _handle_auth_logout(self, send, headers: dict[str, str]) -> bool:
        """Handle POST /auth/logout — clear session."""
        cookie_header = headers.get("cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{self._cookie_name}="):
                token = part[len(self._cookie_name) + 1:]
                self._sessions.pop(token, None)
        resp_body = b'{"ok":true}'
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(resp_body)).encode()),
                (b"set-cookie", f"{self._cookie_name}=; HttpOnly; SameSite=Lax; Max-Age=0; Path=/".encode()),
            ],
        })
        await send({"type": "http.response.body", "body": resp_body})
        return True

    async def _read_http_body(self, receive) -> bytes:
        """Handle read http body."""
        body = b""
        while True:
            event = await receive()
            if event.get("type") != "http.request":
                continue
            body += event.get("body", b"")
            if not event.get("more_body", False):
                break
        return body

    async def _send_bytes(
        self,
        send,
        *,
        status: int,
        body: bytes,
        content_type: str = "text/plain; charset=utf-8",
        close: bool = False,
    ) -> None:
        """Handle send bytes."""
        response_headers = [
            (b"content-type", content_type.encode("utf-8")),
            (b"content-length", str(len(body)).encode("utf-8")),
        ]
        if close:
            response_headers.append((b"connection", b"close"))
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    async def _send_html(self, send, *, status: int, html: str) -> None:
        """Handle send html."""
        await self._send_bytes(
            send,
            status=status,
            body=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )

    async def _send_api_error(
        self,
        send,
        *,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Handle send api error."""
        body = json.dumps(
            _api_error_list_envelope(code=code, message=message, details=details)
        ).encode("utf-8")
        await self._send_bytes(
            send, status=status, body=body, content_type="application/json"
        )

    async def _send_redirect(self, send, *, location: str, status: int = 302) -> None:
        """Handle send redirect."""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"location", location.encode("utf-8"))],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def _send_json(self, send, *, status: int, payload: dict[str, Any]) -> None:
        """Send a JSON response payload."""
        body = json.dumps(payload).encode("utf-8")
        await self._send_bytes(
            send, status=status, body=body, content_type="application/json"
        )

    # ── W28E-1870-B storage change-watch REST surface (PS-102 §5.5) ──────────
    @staticmethod
    def _is_watches_path(path: str) -> bool:
        """Return True for a /v1/watches* (or /api/v1/watches*) REST path."""
        norm = path
        if norm.startswith("/api/v1/watches"):
            norm = norm[len("/api"):]
        return norm == "/v1/watches" or norm.startswith("/v1/watches/") or norm == "/v1/watches/"

    @staticmethod
    def _watch_error_status(exc: Exception) -> int:
        """Map a change-stream error to a truthful HTTP status (PS-102 §5.6)."""
        try:
            from cloud_dog_api_kit.change_stream.errors import (
                CursorExpired,
                JournalTrimmed,
                RateLimited,
                Unauthorised as _CSUnauthorised,
                UnsupportedBackend,
                WatchNotFound,
                WatchPaused,
            )
        except Exception:  # pragma: no cover - foundation always present
            return 400
        if isinstance(exc, WatchNotFound):
            return 404
        if isinstance(exc, _CSUnauthorised):
            return 403
        if isinstance(exc, RateLimited):
            return 429
        if isinstance(exc, (CursorExpired, JournalTrimmed, WatchPaused)):
            return 409
        if isinstance(exc, UnsupportedBackend):
            return 422
        return 400

    async def _handle_watches(
        self, scope, receive, send, *, method: str, path: str, headers: dict[str, str]
    ) -> bool:
        """Dispatch the /v1/watches* REST contract (PS-102 §5.5). Returns True if handled."""
        from urllib.parse import parse_qs, unquote

        from cloud_dog_api_kit.change_stream.errors import ChangeStreamError

        from .guard import _resolve_principal_lightweight

        norm = path
        if norm.startswith("/api/v1/watches"):
            norm = norm[len("/api"):]
        # strip /v1/watches prefix -> the sub-path (id + action)
        sub = norm[len("/v1/watches"):].strip("/")
        qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))

        def _q(name: str, default: str = "") -> str:
            vals = qs.get(name)
            return vals[0] if vals else default

        principal = _resolve_principal_lightweight(self, scope, headers)
        if principal is None:
            await self._send_json(
                send,
                status=401,
                payload={"code": "unauthorised", "message": "authentication required"},
            )
            return True
        actor = str(principal.get("user_id") or "")
        can_write = role_can_write(principal.get("role"))

        def _deny_write() -> bool:
            return not can_write

        async def _write_denied() -> None:
            await self._send_json(
                send,
                status=403,
                payload={"code": "unauthorised", "message": "write permission required"},
            )

        ws = self.watch_service

        async def _body() -> dict[str, Any]:
            try:
                return await self._read_json_body(receive)
            except Exception:
                return {}

        def _tenant(payload: dict[str, Any]) -> str:
            return str(
                payload.get("tenant_id")
                or _q("tenant_id")
                or payload.get("profile")
                or _q("profile")
                or "default"
            )

        try:
            # --- collection routes: /v1/watches ---
            if sub == "":
                if method == "POST":
                    if _deny_write():
                        await _write_denied()
                        return True
                    payload = await _body()
                    result = ws.create_watch(
                        profile_id=str(payload.get("profile") or payload.get("profile_id") or "default"),
                        tenant_id=_tenant(payload),
                        actor=actor,
                        backend=str(payload.get("backend") or ""),
                        criteria=payload.get("criteria") if isinstance(payload.get("criteria"), dict) else None,
                        max_batch=int(payload.get("max_batch", 100)),
                        max_inflight=int(payload.get("max_inflight", 4)),
                        journal_max=int(payload.get("journal_max", 1000)),
                        journal_ttl_seconds=(
                            float(payload["journal_ttl_seconds"])
                            if payload.get("journal_ttl_seconds") not in (None, "")
                            else None
                        ),
                    )
                    await self._send_json(send, status=201, payload=result)
                    return True
                if method == "GET":
                    tenant = str(_q("tenant_id") or _q("profile") or "default")
                    await self._send_json(
                        send, status=200, payload={"watches": ws.list_watches(tenant_id=tenant)}
                    )
                    return True
                await self._send_json(send, status=405, payload={"code": "error", "message": "method not allowed"})
                return True

            # --- item routes: /v1/watches/{id}[/action] ---
            parts = [unquote(p) for p in sub.split("/")]
            watch_id = parts[0]
            action = parts[1] if len(parts) > 1 else ""

            if action == "" and method == "GET":
                tenant = str(_q("tenant_id") or _q("profile") or "default")
                await self._send_json(send, status=200, payload=ws.get_watch(watch_id, tenant_id=tenant))
                return True
            if action == "" and method == "DELETE":
                if _deny_write():
                    await _write_denied()
                    return True
                tenant = str(_q("tenant_id") or _q("profile") or "default")
                await self._send_json(send, status=200, payload=ws.delete(watch_id, tenant_id=tenant))
                return True
            if action == "status" and method == "GET":
                tenant = str(_q("tenant_id") or _q("profile") or "default")
                await self._send_json(send, status=200, payload=ws.get_status(watch_id, tenant_id=tenant))
                return True
            if action == "events" and method == "GET":
                tenant = str(_q("tenant_id") or _q("profile") or "default")
                mb = _q("max_batch")
                await self._send_json(
                    send,
                    status=200,
                    payload=ws.get_batch(
                        watch_id,
                        tenant_id=tenant,
                        since_cursor=_q("since_cursor") or None,
                        max_batch=int(mb) if mb else None,
                    ),
                )
                return True
            if action == "ack" and method == "POST":
                payload = await _body()
                tenant = _tenant(payload)
                if "ack_cursor" not in payload:
                    await self._send_json(send, status=422, payload={"code": "error", "message": "ack_cursor is required"})
                    return True
                await self._send_json(
                    send, status=200, payload=ws.ack(watch_id, tenant_id=tenant, ack_cursor=str(payload["ack_cursor"]))
                )
                return True
            if action == "recover" and method == "POST":
                payload = await _body()
                tenant = _tenant(payload)
                await self._send_json(
                    send,
                    status=200,
                    payload=ws.recover(watch_id, tenant_id=tenant, since_cursor=payload.get("since_cursor") or None),
                )
                return True
            if action == "pause" and method == "POST":
                if _deny_write():
                    await _write_denied()
                    return True
                payload = await _body()
                await self._send_json(send, status=200, payload=ws.pause(watch_id, tenant_id=_tenant(payload)))
                return True
            if action == "resume" and method == "POST":
                if _deny_write():
                    await _write_denied()
                    return True
                payload = await _body()
                await self._send_json(send, status=200, payload=ws.resume(watch_id, tenant_id=_tenant(payload)))
                return True
            if action in {"test-event", "test_event"} and method == "POST":
                if _deny_write():
                    await _write_denied()
                    return True
                payload = await _body()
                tenant = _tenant(payload)
                extra = {
                    k: v
                    for k, v in payload.items()
                    if k not in {"tenant_id", "profile", "profile_id", "action", "object_ref"}
                }
                await self._send_json(
                    send,
                    status=200,
                    payload=ws.test_event(
                        watch_id,
                        tenant_id=tenant,
                        action=str(payload.get("action", "created")),
                        object_ref=str(payload.get("object_ref", "test")),
                        **extra,
                    ),
                )
                return True

            await self._send_json(send, status=404, payload={"code": "error", "message": "unknown watch route"})
            return True
        except ChangeStreamError as exc:
            detail = getattr(exc, "to_dict", lambda: {"code": "error", "message": str(exc)})()
            await self._send_json(send, status=self._watch_error_status(exc), payload=detail)
            return True
        except Exception as exc:  # pragma: no cover - defensive; never leak a 500 stack
            await self._send_json(send, status=400, payload={"code": "error", "message": str(exc)})
            return True

    async def _publish_cfg_event(
        self,
        *,
        resource: str,
        action: str,
        identifier: str,
        actor: Optional[str] = None,
        before: Optional[dict[str, Any]] = None,
        after: Optional[dict[str, Any]] = None,
    ) -> None:
        """CFG-06: publish a config-change event via the platform broadcaster.

        Best-effort: failures are logged but never raised, so the CRUD HTTP
        response is never blocked by a broadcast issue.
        """
        broadcaster = self.config_event_broadcaster
        if broadcaster is None:
            return
        try:
            # Redact secrets so subscribers never see tokens.
            safe_after = _redact_secrets(after) if isinstance(after, dict) else after
            safe_before = _redact_secrets(before) if isinstance(before, dict) else before
            await broadcaster.publish(
                ConfigChangeEvent(
                    service="file-mcp-server",
                    resource=resource,
                    action=action,
                    identifier=str(identifier or ""),
                    actor=actor,
                    before=safe_before,
                    after=safe_after,
                )
            )
        except Exception as exc:  # noqa: BLE001
            if self.logger is not None:
                self.logger.warning(
                    "Failed to publish config change event",
                    resource=resource,
                    action=action,
                    identifier=identifier,
                    error=str(exc),
                )

    def _ui_index_path(self) -> Path:
        """Return the configured SPA index path."""
        return self.ui_dist_path / "index.html"

    @staticmethod
    def _ui_route_paths() -> tuple[str, ...]:
        """Return root routes owned by the file-mcp SPA."""
        return (
            "/",
            "/login",
            "/dashboard",
            "/catalogue",
            "/file-browser",
            "/search",
            "/storage-profiles",
            "/profiles",
            "/source-connections",
            "/audit-log",
            "/developer/api-docs",
            "/developer/mcp-console",
            "/developer/a2a-console",
            "/system/jobs",
            "/system/settings",
            "/system/about",
            "/idam",
            "/idam/users",
            "/idam/groups",
            "/idam/api-keys",
            "/idam/roles",
            "/idam/rbac",
            "/admin-identity",
            "/admin/identity",
            "/admin/users",
            "/admin/groups",
            "/admin/api-keys",
            "/admin/roles",
            "/admin/rbac",
            "/google-drive-settings",
            "/api-docs",
            "/mcp-console",
            "/a2a-console",
            "/jobs",
            "/settings",
            "/about",
        )

    @staticmethod
    def _canonical_ui_aliases() -> dict[str, str]:
        """Return legacy WebUI aliases that must redirect to canonical routes."""
        return {
            "/ui/login": "/login",
            "/auth/login": "/login",
            "/dashboard": "/",
            "/file-browser": "/catalogue",
            "/audit": "/audit-log",
            "/diagnostics-audit": "/audit-log",
            "/observability": "/audit-log",
            "/logs": "/audit-log",
            "/profiles": "/storage-profiles",
            "/source-connections": "/storage-profiles",
            "/idam": "/admin/users",
            "/idam/users": "/admin/users",
            "/idam/groups": "/admin/groups",
            "/idam/api-keys": "/admin/api-keys",
            "/apikeys": "/admin/api-keys",
            "/api-keys": "/admin/api-keys",
            "/-keys": "/admin/api-keys",
            "/idam/roles": "/admin/roles",
            "/idam/rbac": "/admin/rbac",
            "/rbac": "/admin/rbac",
            "/admin-identity": "/admin/users",
            "/admin/identity": "/admin/users",
            "/admin-rbac": "/admin/rbac",
            "/api-docs": "/developer/api-docs",
            "/-docs": "/developer/api-docs",
            "/docs": "/developer/api-docs",
            "/openapi": "/developer/api-docs",
            "/mcp": "/developer/mcp-console",
            "/mcp-console": "/developer/mcp-console",
            "/a2a": "/developer/a2a-console",
            "/a2a-console": "/developer/a2a-console",
            "/jobs": "/system/jobs",
            "/settings": "/system/settings",
            "/about": "/system/about",
        }

    def _canonical_ui_redirect_location(self, path: str, query_string: bytes) -> str | None:
        """Return the 308 target for a legacy WebUI alias, preserving query strings."""
        target = self._canonical_ui_aliases().get(path)
        if target is None:
            return None
        if query_string:
            return f"{target}?{query_string.decode('utf-8', errors='ignore')}"
        return target

    def _is_ui_route(self, path: str) -> bool:
        """Return True if request path should serve the SPA entrypoint."""
        if path in self._ui_route_paths():
            return True
        if path == self.ui_base_path:
            return True
        if path.startswith(f"{self.ui_base_path}/"):
            return not (
                path == f"{self.ui_base_path}/assets"
                or path.startswith(f"{self.ui_base_path}/assets/")
            )
        if self._is_ui_fallback_route(path):
            return True
        return False

    @staticmethod
    def _is_ui_fallback_route(path: str) -> bool:
        """Return True for non-API navigation paths that should fall back to SPA."""
        return False

    def _is_write_gated_data_path(self, path: str) -> bool:
        """Return True for DATA surfaces a read-only flat role may not mutate.

        Thread-a (W28A-728-R4): the read-only write-gate only applies to the
        data/mutation surfaces — ``/api``, ``/v1``, ``/webmcp``/``/mcp``,
        ``/a2a``/``/weba2a``, ``/admin`` CRUD. It must NOT swallow the auth
        endpoints (login/logout have their own handling and read-only must still
        be able to log in/out) nor any health/readiness probe. Read methods are
        never gated — read-only is a VIEW role.
        """
        if not path.startswith("/"):
            return False
        # Never gate auth/login/logout or health/readiness/liveness probes.
        if path.startswith("/auth/") or path in {"/auth", "/login", "/logout"}:
            return False
        if path.endswith("/health") or path in {
            "/health",
            "/status",
            "/ready",
            "/live",
            self.health_path,
            self._ready_path(),
            self._live_path(),
        }:
            return False
        gated_prefixes = (
            "/api",
            "/v1",
            "/webapi",
            "/weba2a",
            "/a2a",
            "/admin",
            "/events",
            "/tasks",
            "/files",
        )
        for prefix in gated_prefixes:
            if not prefix:
                continue
            if path == prefix or path.startswith(f"{prefix.rstrip('/')}/"):
                return True
        return False

    def _resolve_ui_asset_path(self, path: str) -> Path | None:
        """Resolve an asset path under ui/dist while preventing traversal."""
        relative_path = ""
        if path.startswith("/assets/"):
            relative_path = path.lstrip("/")
        elif path.startswith(f"{self.ui_base_path}/assets/"):
            relative_path = path[len(f"{self.ui_base_path}/") :]
        if not relative_path:
            return None

        candidate_str = path_utils.resolve_path(str(self.ui_dist_path / relative_path))
        if not path_utils.is_relative_to(candidate_str, str(self.ui_dist_path)):
            return None
        if not path_utils.is_file(candidate_str):
            return None
        return path_utils.as_path(candidate_str)

    async def _send_file(self, send, *, path: Path, method: str) -> None:
        """Send a file response for GET/HEAD requests."""
        body = path_utils.read_bytes(str(path))
        content_type = mimetypes.guess_type(path_utils.name(str(path)))[0] or "application/octet-stream"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", content_type.encode("utf-8")),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"" if method == "HEAD" else body,
            }
        )

    def _runtime_config_payload(self) -> dict[str, str]:
        """Build runtime-config values for the UI bootstrap script."""
        env_name = str(read_env_var("FILE_MCP_UI_ENV") or read_env_var("CLOUD_DOG_ENV") or "dev")
        env_name = env_name.strip() or "dev"

        api_base_url = str(read_env_var("FILE_MCP_UI_API_BASE_URL") or "").strip() or "/"
        auth_mode = str(read_env_var("FILE_MCP_UI_AUTH_MODE") or "cookie").strip() or "cookie"
        if auth_mode not in {"api_key", "cookie", "oidc"}:
            auth_mode = "api_key"

        selected_profile_payload = None
        for profile_payload in self._list_profile_payloads():
            if str(profile_payload.get("name") or "") == self.profile_name:
                selected_profile_payload = profile_payload
                break
        selected_profile_config = (
            selected_profile_payload.get("profile")
            if isinstance(selected_profile_payload, dict)
            else {}
        )
        scope_roots: list[str] = []
        if isinstance(selected_profile_config, dict):
            scope_cfg = selected_profile_config.get("scope")
            if isinstance(scope_cfg, dict):
                roots = scope_cfg.get("roots") or []
                if isinstance(roots, list):
                    scope_roots = [str(root or "").strip() for root in roots if str(root or "").strip()]

        browse_path_raw = str(read_env_var("FILE_MCP_UI_DEFAULT_BROWSE_PATH") or "").strip()
        default_browse_path = browse_path_raw
        if not default_browse_path and scope_roots:
            default_browse_path = "."
        if not default_browse_path:
            default_browse_path = "/workspace"

        audit_log_path_raw = str(read_env_var("FILE_MCP_UI_AUDIT_LOG_PATH") or "").strip()
        audit_log_path = audit_log_path_raw
        audit_from_profile = False
        if not audit_log_path and isinstance(selected_profile_config, dict):
            audit_cfg = selected_profile_config.get("audit")
            if isinstance(audit_cfg, dict):
                audit_log_path = str(audit_cfg.get("log_path") or "").strip()
                audit_from_profile = bool(audit_log_path)
        if not audit_log_path:
            audit_log_path = "/data/audit/audit.jsonl"
        if audit_from_profile and scope_roots:
            audit_log_path = _profile_ui_relative_path(audit_log_path, scope_roots)

        profile_store_path = (
            str(read_env_var("FILE_MCP_UI_PROFILE_STORE_PATH") or "").strip()
            or ""
        )
        # In cookie auth mode the WebUI must call /webmcp (session-cookie auth).
        # The standard /mcp endpoint requires a Bearer API key.
        mcp_base_url_raw = str(read_env_var("FILE_MCP_UI_MCP_BASE_URL") or "").strip()
        if mcp_base_url_raw:
            mcp_base_url = mcp_base_url_raw
        elif auth_mode == "cookie":
            mcp_base_url = "/webmcp"
        else:
            mcp_base_url = "/mcp"
        a2a_base_url = str(read_env_var("FILE_MCP_UI_A2A_BASE_URL") or "").strip() or "/a2a"
        session_timeout = _to_int(
            read_env_var("CLOUD_DOG_SESSION_TIMEOUT_MINUTES"), default=30
        )
        app_version = str(read_env_var("FILE_MCP_VERSION") or "").strip() or self._read_pyproject_version() or "0.0.0"
        # W28E-1863 fix-wave-b (WSC-014 / PS-30 UI-R7.3): surface build identity to
        # the WebUI bootstrap so the shared AboutPage can render commit/build-date.
        _build = self._build_identity()

        return {
            "ENV": env_name,
            "API_BASE_URL": api_base_url,
            "MCP_BASE_URL": mcp_base_url,
            "A2A_BASE_URL": a2a_base_url,
            "AUTH_MODE": auth_mode,
            "SESSION_TIMEOUT_MINUTES": str(session_timeout),
            "APP_VERSION": app_version,
            "APP_COMMIT": _build["source_commit"],
            "APP_BUILD_DATE": _build["build_date"],
            "APP_CONTAINER_DIGEST": _build["container_digest"],
            "APP_ENV": _build["environment"],
            "AUDIT_LOG_PATH": audit_log_path,
            "DEFAULT_BROWSE_PATH": default_browse_path,
            "PROFILE_STORE_PATH": profile_store_path,
            "PROFILE_API_PATH": "/admin/profiles",
        }

    def _selected_profile_payload(self) -> dict[str, Any] | None:
        """Return the active profile payload, if present."""
        for profile_payload in self._list_profile_payloads():
            if str(profile_payload.get("name") or "") == self.profile_name:
                return profile_payload
        return None

    def _admin_runtime_config_payload(self) -> dict[str, Any]:
        """Return a read-only runtime snapshot for the settings UI."""
        runtime_payload = self._runtime_config_payload()
        selected_profile = self._selected_profile_payload()
        return {
            "service": {
                "name": self.app_name,
                "profile": self.profile_name,
                "transport": self.transport,
                "env_file": self.env_file,
                "config_path": self.active_config,
                "defaults_path": str(
                    read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or ""
                ).strip()
                or None,
                "api_base_url": str(runtime_payload.get("API_BASE_URL") or ""),
                "mcp_base_url": str(runtime_payload.get("MCP_BASE_URL") or "/mcp"),
                "a2a_base_url": str(runtime_payload.get("A2A_BASE_URL") or "/a2a"),
                "auth_mode": str(runtime_payload.get("AUTH_MODE") or "api_key"),
            },
            "status": self._status_payload(),
            "health": self._health_response_payload(),
            "profiles": self._list_profile_payloads(),
            "selected_profile": selected_profile,
        }

    def _effective_config_payload(self, *, reveal: bool = False) -> dict[str, Any]:
        """Return the PS-73 effective config tree with PS-81 source metadata."""
        if self.config is not None:
            config_payload = _jsonish_model_dump(self.config)
        else:
            defaults_path = str(read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or "").strip()
            try:
                loaded = load_config(
                    env_path=self.env_file,
                    config_path=self.active_config,
                    defaults_path=defaults_path or None,
                )
                config_payload = _jsonish_model_dump(loaded)
            except Exception:
                config_payload = self._load_config_document()

        if not isinstance(config_payload, dict):
            config_payload = {"profiles": {}}
        config_payload = self._deep_copy_jsonish(config_payload)

        profiles = config_payload.setdefault("profiles", {})
        if isinstance(profiles, dict):
            for profile_payload in self._list_profile_payloads():
                name = str(profile_payload.get("name") or "").strip()
                profile = profile_payload.get("profile")
                if name and isinstance(profile, dict):
                    profiles[name] = self._deep_copy_jsonish(profile)

        raw_config = self._load_config_document()
        raw_config_paths = set(_effective_config_leaf_paths(raw_config))
        default_config_paths = set(_effective_config_leaf_paths(self._load_defaults_document()))
        sources: dict[str, dict[str, Any]] = {}
        for key_path in _effective_config_leaf_paths(config_payload):
            from_config = key_path in raw_config_paths
            origin = "default"
            source = "default"
            if from_config:
                source = "config"
                origin = "config-addition" if key_path not in default_config_paths else "config"
            sources[key_path] = {
                "source": source,
                "source_detail": self.active_config if from_config else "defaults.yaml",
                "origin": origin,
                "secret": _effective_config_is_secret_path(key_path),
                "servers": _effective_config_server_scope(key_path),
            }

        redacted_config = (
            config_payload
            if reveal
            else _effective_config_redact(config_payload, sources)
        )
        total_keys = len(sources)
        secret_keys = sum(1 for item in sources.values() if item.get("secret"))
        per_server: dict[str, int] = {}
        for meta in sources.values():
            for server in meta.get("servers") or ["shared"]:
                server_name = str(server)
                per_server[server_name] = per_server.get(server_name, 0) + 1

        return {
            "ok": True,
            "config": redacted_config,
            "sources": sources,
            "servers": ["all", "api", "mcp", "a2a", "webui"],
            "counts": {
                "total_keys": total_keys,
                "secret_keys": secret_keys,
                "config_only_additions": sum(
                    1 for item in sources.values() if item.get("origin") == "config-addition"
                ),
                "per_server": per_server,
            },
            "secrets_redacted": not reveal,
        }

    def _openapi_payload(self) -> dict[str, Any]:
        """Return a compact OpenAPI description for the Web UI docs page."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "Cloud-Dog File MCP API",
                "version": self.version,
                "description": "Operational HTTP, admin, MCP, and A2A surface for file-mcp-server.",
            },
            "servers": [{"url": "/"}],
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health",
                        "responses": {"200": {"description": "Health payload"}},
                    }
                },
                "/status": {
                    "get": {
                        "summary": "Runtime status",
                        "responses": {"200": {"description": "Status payload"}},
                    }
                },
                "/auth/login": {
                    "post": {
                        "summary": "Cookie login",
                        "responses": {"200": {"description": "Login success"}},
                    }
                },
                "/auth/me": {
                    "get": {
                        "summary": "Current session user",
                        "responses": {"200": {"description": "Authenticated user"}},
                    }
                },
                "/auth/logout": {
                    "post": {
                        "summary": "Logout",
                        "responses": {"200": {"description": "Logout success"}},
                    }
                },
                "/admin/users": {
                    "get": {"summary": "List admin users", "responses": {"200": {"description": "Users"}}},
                    "post": {"summary": "Create admin user", "responses": {"201": {"description": "User created"}}},
                },
                "/admin/groups": {
                    "get": {"summary": "List admin groups", "responses": {"200": {"description": "Groups"}}},
                    "post": {"summary": "Create admin group", "responses": {"201": {"description": "Group created"}}},
                },
                "/admin/api-keys": {
                    "get": {"summary": "List admin API keys", "responses": {"200": {"description": "API keys"}}},
                    "post": {"summary": "Create admin API key", "responses": {"201": {"description": "API key created"}}},
                },
                "/admin/roles": {
                    "get": {"summary": "List roles", "responses": {"200": {"description": "Roles"}}},
                    "post": {"summary": "Create role", "responses": {"201": {"description": "Role created"}}},
                },
                "/admin/profiles": {
                    "get": {"summary": "List storage profiles", "responses": {"200": {"description": "Profiles"}}},
                    "post": {"summary": "Create storage profile", "responses": {"201": {"description": "Profile created"}}},
                },
                "/admin/runtime-config": {
                    "get": {
                        "summary": "Read-only runtime config snapshot",
                        "responses": {"200": {"description": "Runtime config"}},
                    }
                },
                "/admin/effective-config": {
                    "get": {
                        "summary": "PS-73 effective config with source attribution",
                        "responses": {"200": {"description": "Effective config"}},
                    }
                },
                "/admin/reload": {
                    "post": {"summary": "Reload active configuration", "responses": {"200": {"description": "Reload result"}}},
                },
                "/mcp": {
                    "post": {"summary": "JSON-RPC MCP endpoint", "responses": {"200": {"description": "MCP response"}}},
                },
                "/a2a/health": {
                    "get": {"summary": "A2A health", "responses": {"200": {"description": "A2A status"}}},
                },
            },
        }

    async def _serve_runtime_config(self, send, *, method: str) -> None:
        """Serve runtime configuration bootstrap JavaScript.

        The script emits server-provided defaults while preserving any
        previously injected runtime overrides (for example Playwright init
        scripts in E2E tests).
        """
        payload = self._runtime_config_payload()
        def _url_expr(value: str, *, fallback: str) -> str:
            raw = value.strip()
            if not raw:
                raw = fallback
            if raw == "/":
                return "__origin"
            if raw.startswith("/"):
                return f"__origin + {json.dumps(raw)}"
            return json.dumps(raw)

        api_base_expr = _url_expr(
            str(payload.get("API_BASE_URL", "")), fallback="/api"
        )
        mcp_base_expr = json.dumps(str(payload.get("MCP_BASE_URL", "/mcp")) or "/mcp")
        a2a_base_expr = json.dumps(str(payload.get("A2A_BASE_URL", "/a2a")) or "/a2a")

        body = (
            "const __origin = window.location.origin;\n"
            "window.__RUNTIME_CONFIG__ = Object.assign(\n"
            "  {\n"
            f'    "ENV": {json.dumps(payload.get("ENV", "dev"))},\n'
            f'    "API_BASE_URL": {api_base_expr},\n'
            f'    "MCP_BASE_URL": {mcp_base_expr},\n'
            f'    "A2A_BASE_URL": {a2a_base_expr},\n'
            f'    "AUTH_MODE": {json.dumps(payload.get("AUTH_MODE", "cookie"))},\n'
            f'    "SESSION_TIMEOUT_MINUTES": {json.dumps(_to_int(payload.get("SESSION_TIMEOUT_MINUTES"), default=30))},\n'
            f'    "APP_VERSION": {json.dumps(payload.get("APP_VERSION", "0.0.0"))},\n'
            f'    "APP_COMMIT": {json.dumps(payload.get("APP_COMMIT", ""))},\n'
            f'    "APP_BUILD_DATE": {json.dumps(payload.get("APP_BUILD_DATE", ""))},\n'
            f'    "APP_CONTAINER_DIGEST": {json.dumps(payload.get("APP_CONTAINER_DIGEST", ""))},\n'
            f'    "APP_ENV": {json.dumps(payload.get("APP_ENV", ""))},\n'
            f'    "AUDIT_LOG_PATH": {json.dumps(payload.get("AUDIT_LOG_PATH", ""))},\n'
            f'    "DEFAULT_BROWSE_PATH": {json.dumps(payload.get("DEFAULT_BROWSE_PATH", "src"))},\n'
            f'    "PROFILE_STORE_PATH": {json.dumps(payload.get("PROFILE_STORE_PATH", ""))},\n'
            f'    "PROFILE_API_PATH": {json.dumps(payload.get("PROFILE_API_PATH", "/admin/profiles"))}\n'
            "  },\n"
            "  window.__RUNTIME_CONFIG__ || {}\n"
            ");\n"
        )
        script = body.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"application/javascript; charset=utf-8"),
                    (b"cache-control", b"no-store"),
                    (b"content-length", str(len(script)).encode("utf-8")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"" if method == "HEAD" else script,
            }
        )

    async def _serve_spa_index(self, send, *, method: str) -> None:
        """Serve SPA entrypoint from ui/dist."""
        index_path = self._ui_index_path()
        if not path_utils.is_file(str(index_path)):
            await self._send_html(
                send,
                status=503,
                html="<h1>UI not built</h1><p>Expected ui/dist/index.html.</p>",
            )
            return
        await self._send_file(send, path=index_path, method=method)

    async def _read_json_body(self, receive) -> dict[str, Any]:
        """Read and decode a JSON request body."""
        body = await self._read_http_body(receive)
        if not body:
            return {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise AdminIdentityError(
                "VALIDATION_ERROR", f"invalid JSON body: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise AdminIdentityError(
                "VALIDATION_ERROR", "JSON body must be an object"
            )
        return payload

    @staticmethod
    def _extract_auth_token(raw_header: str, scheme: str | None) -> str | None:
        """Handle extract auth token."""
        value = raw_header.strip()
        if not value:
            return None
        if scheme:
            prefix = f"{scheme} "
            if not value.lower().startswith(prefix.lower()):
                return None
            token = value[len(prefix) :].strip()
            return token or None
        return value

    async def _authenticate_request(
        self, *, scope: dict[str, Any], headers: dict[str, str]
    ) -> tuple[Any | None, str]:
        """Resolve auth token for a request and return auth-info/profile."""
        verifier = self.a2a_auth_verifier
        if verifier is None:
            session = self._get_session_from_cookie(headers)
            if session is not None:
                # W28A-742 (PS-82 §3.1): NEVER default a missing role to
                # "admin". Authenticated-but-empty sessions get the role
                # the cookie actually carries (empty string if missing);
                # the W28A-742 route-guard chokepoint enforces the
                # authorise() decision, so a default-admin can no longer
                # slip through.
                return (
                    SimpleNamespace(
                        subject=session.get("user_id", "1"),
                        scopes=["*"] if session.get("role") == "admin" else [],
                        roles=[str(session.get("role") or "")],
                    ),
                    self.profile_name,
                )
            return (None, self.profile_name)

        conn = HTTPConnection(scope)
        profile_name = self.profile_name
        if hasattr(verifier, "resolve_profile") and callable(
            getattr(verifier, "resolve_profile")
        ):
            try:
                profile_name = str(verifier.resolve_profile(conn))
            except Exception:
                profile_name = self.profile_name

        token: str | None = None
        if hasattr(verifier, "resolve_request_credential") and callable(
            getattr(verifier, "resolve_request_credential")
        ):
            try:
                token, _failure_reason = verifier.resolve_request_credential(
                    headers, profile_name
                )
            except Exception:
                token = None
        else:
            header_name = "authorization"
            header_scheme: str | None = "Bearer"
            if hasattr(verifier, "header_for_profile") and callable(
                getattr(verifier, "header_for_profile")
            ):
                try:
                    resolved_header_name, resolved_header_scheme = (
                        verifier.header_for_profile(profile_name)
                    )
                    header_name = (
                        str(resolved_header_name).strip().lower() or "authorization"
                    )
                    header_scheme = resolved_header_scheme
                except Exception:
                    header_name = "authorization"
                    header_scheme = "Bearer"
            raw_header = headers.get(header_name, "")
            token = self._extract_auth_token(raw_header, header_scheme)
        if not token:
            session = self._get_session_from_cookie(headers)
            if session is not None:
                # W28A-742 (PS-82 §3.1): NEVER default a missing role to
                # "admin". Authenticated-but-empty sessions get the role
                # the cookie actually carries (empty string if missing);
                # the W28A-742 route-guard chokepoint enforces the
                # authorise() decision, so a default-admin can no longer
                # slip through.
                return (
                    SimpleNamespace(
                        subject=session.get("user_id", "1"),
                        scopes=["*"] if session.get("role") == "admin" else [],
                        roles=[str(session.get("role") or "")],
                    ),
                    profile_name,
                )
            return (None, profile_name)

        if hasattr(verifier, "verify_token_for_profile") and callable(
            getattr(verifier, "verify_token_for_profile")
        ):
            auth_info = await verifier.verify_token_for_profile(token, profile_name)
        elif hasattr(verifier, "verify_token") and callable(
            getattr(verifier, "verify_token")
        ):
            auth_info = await verifier.verify_token(token)
        else:
            return (None, profile_name)
        return (auth_info, profile_name)

    @staticmethod
    def _token_scopes(auth_info: Any | None) -> set[str]:
        """Extract scopes from a token object."""
        if auth_info is None:
            return set()
        raw = getattr(auth_info, "scopes", None) or []
        return {str(scope).strip() for scope in raw if str(scope).strip()}

    @staticmethod
    def _has_admin_scope(scopes: set[str]) -> bool:
        """Return True if scope set represents administrative access."""
        return (
            "*" in scopes
            or "admin" in scopes
            or "role:admin" in scopes
            or "admin:*" in scopes
        )

    def _has_google_drive_admin_scope(self, scopes: set[str]) -> bool:
        """Return True when scopes grant Google Drive admin access."""
        return self._has_admin_scope(scopes) or "admin:google_drive" in scopes

    # ── W28C-1702 (FM6/FM2) security helpers ──────────────────────────────

    async def _admin_gate(self, *, scope, headers: dict[str, str]):
        """Canonical admin-auth gate (the one /admin/profiles uses).

        W28C-1702 (FM6): accepts an admin X-API-Key OR an admin-scope session
        cookie OR the x-admin-token; there is NO ``legacy_open_access`` anon
        bypass (that bypass is what leaked the google_drive OAuth client_id).
        Returns ``(is_authenticated, is_admin, principal_id)``.
        """
        supplied_admin_token = headers.get("x-admin-token", "")
        ui_admin = bool(
            self.admin_ui_token and supplied_admin_token == self.admin_ui_token
        )
        auth_info, _sel = await self._authenticate_request(scope=scope, headers=headers)
        cookie_session = self._get_session_from_cookie(headers)
        cookie_admin = (
            cookie_session is not None and cookie_session.get("role") == "admin"
        )
        scopes = self._token_scopes(auth_info)
        token_admin = self._has_admin_scope(scopes) or self._has_google_drive_admin_scope(scopes)
        is_authenticated = ui_admin or cookie_admin or auth_info is not None
        is_admin = ui_admin or cookie_admin or token_admin
        principal_id = ""
        if cookie_session is not None:
            principal_id = str(cookie_session.get("user") or "")
        elif auth_info is not None:
            principal_id = str(self._auth_user_payload(auth_info).get("id") or "")
        elif ui_admin:
            principal_id = "admin-ui-token"
        return is_authenticated, is_admin, principal_id

    async def _deny_admin_access(self, send, *, headers: dict[str, str]) -> None:
        """Anon denial for protected admin routes: 302→login for a browser,
        401 JSON otherwise (W28C-1702 FM6)."""
        accept = headers.get("accept", "")
        if "text/html" in accept:
            await self._send_redirect(send, location="/auth/login?next=/storage-profiles")
        else:
            await self._send_api_error(
                send, status=401, code="UNAUTHENTICATED", message="Unauthorised"
            )

    @staticmethod
    def _redact_profile_secrets(obj: Any) -> Any:
        """W28C-1702 (FM2): deep-mask secret values in profile/runtime JSON.

        Masks the storage secret keys (s3 access_key/secret_key, webdav/ftp
        password, google_drive client_secret/refresh_token/access_token) plus
        profile auth api_keys, anywhere they appear. Returns a redacted COPY;
        the source data is untouched so the owning-admin /secrets reveal path
        can still serve cleartext.
        """
        redaction = "***REDACTED***"
        secret_keys = {
            "access_key",
            "secret_key",
            "secret_access_key",
            "password",
            "client_secret",
            "refresh_token",
            "access_token",
            "api_key",
        }

        def _walk(node: Any) -> Any:
            if isinstance(node, dict):
                out: dict[str, Any] = {}
                for key, value in node.items():
                    if key == "api_keys" and isinstance(value, list):
                        out[key] = [redaction if str(item) else item for item in value]
                    elif key in secret_keys and isinstance(value, str) and value:
                        out[key] = redaction
                    else:
                        out[key] = _walk(value)
                return out
            if isinstance(node, list):
                return [_walk(item) for item in node]
            return node

        return _walk(obj)

    def _load_config_document(self) -> dict[str, Any]:
        """Load active config YAML as mutable dictionary."""
        config_path_str = self.active_config
        if not path_utils.exists(config_path_str):
            return {"profiles": {}}
        try:
            parsed = load_yaml(config_path_str, missing_ok=True)
        except Exception:
            return {"profiles": {}}
        if not isinstance(parsed, dict):
            return {"profiles": {}}
        if not isinstance(parsed.get("profiles"), dict):
            parsed["profiles"] = {}
        return parsed

    def _load_defaults_document(self) -> dict[str, Any]:
        """Load defaults YAML for effective-config source attribution."""
        defaults_path_str = str(
            read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or "defaults.yaml"
        ).strip()
        if not defaults_path_str or not path_utils.exists(defaults_path_str):
            return {}
        try:
            parsed = load_yaml(defaults_path_str, missing_ok=True)
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return parsed

    async def _is_a2a_authorized(
        self, *, scope: dict[str, Any], headers: dict[str, str]
    ) -> bool:
        """Handle is a2a authorized."""
        auth_info, _ = await self._authenticate_request(scope=scope, headers=headers)
        return auth_info is not None

    def _resolve_config_value(self, value: Any) -> str:
        """Handle resolve config value."""
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", text)
        if not match:
            return text
        return str(read_env_var(match.group(1), "")).strip()

    def _configured_value(self, value: Any) -> str:
        """Handle configured value."""
        text = self._resolve_config_value(value)
        if not text or "${" in text:
            return ""
        return text

    def _compute_callback_url(
        self, scope: dict[str, Any], headers: dict[str, str]
    ) -> str:
        """Handle compute callback url."""
        forwarded_proto = (
            (headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        )
        if forwarded_proto in {"http", "https"}:
            scheme = forwarded_proto
        else:
            scheme = scope.get("scheme") or "http"
        host = headers.get("host") or self.callback_host_fallback
        return f"{scheme}://{host}/admin/google-drive/callback"

    def _load_google_profile_values(
        self, *, profile_name: str, callback_url: str
    ) -> dict[str, str]:
        """Handle load google profile values."""
        empty_values = {
            "user_email": "",
            "folder_input": "",
            "client_id": "",
            "client_secret": "",
            "folder_url_example": "",
            "oauth_scope": "",
            "oauth_authorize_uri": "",
            "api_base_uri": "",
            "redirect_uri": callback_url,
            "token_uri": "",
        }

        def _values_from_drive(raw_drive: dict[str, Any]) -> dict[str, str]:
            folder_url = self._configured_value(raw_drive.get("folder_url"))
            folder_id = self._configured_value(raw_drive.get("folder_id"))
            configured_redirect = self._configured_value(raw_drive.get("redirect_uri"))
            redirect_uri = (
                callback_url
                if configured_redirect.strip().lower() == OOB_REDIRECT_URI
                else (configured_redirect or callback_url)
            )
            return {
                "user_email": self._configured_value(raw_drive.get("user_email")),
                "folder_input": folder_url or folder_id,
                "client_id": self._configured_value(raw_drive.get("client_id")),
                "client_secret": self._configured_value(raw_drive.get("client_secret")),
                "folder_url_example": self._configured_value(
                    raw_drive.get("folder_url_example")
                ),
                "oauth_scope": self._configured_value(raw_drive.get("oauth_scope")),
                "oauth_authorize_uri": self._configured_value(
                    raw_drive.get("oauth_authorize_uri")
                ),
                "api_base_uri": self._configured_value(raw_drive.get("api_base_uri")),
                "redirect_uri": redirect_uri,
                "token_uri": self._configured_value(raw_drive.get("token_uri")),
            }

        for item in self._list_profile_payloads():
            if item.get("name") != profile_name:
                continue
            prof = item.get("profile") if isinstance(item, dict) else {}
            storage = prof.get("storage") if isinstance(prof, dict) else {}
            raw_drive = storage.get("google_drive") if isinstance(storage, dict) else {}
            if isinstance(raw_drive, dict):
                db_values = _values_from_drive(raw_drive)
                if any(
                    db_values.get(key)
                    for key in (
                        "user_email",
                        "folder_input",
                        "client_id",
                        "client_secret",
                        "token_uri",
                    )
                ):
                    return db_values

        defaults_path = str(read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or "").strip()
        try:
            cfg = load_config(
                env_path=self.env_file,
                config_path=self.active_config,
                defaults_path=defaults_path or None,
            )
            profile = cfg.profiles.get(profile_name) or cfg.profiles.get(
                self.profile_name
            )
            if profile is None:
                return empty_values
            drive = profile.storage.google_drive
            return _values_from_drive(drive.model_dump())
        except Exception:
            config_path_str = self.active_config
            if not path_utils.exists(config_path_str):
                return empty_values
            try:
                parsed = load_yaml(config_path_str, missing_ok=True)
                profiles = parsed.get("profiles")
                if not isinstance(profiles, dict):
                    return empty_values
                raw_profile = profiles.get(profile_name) or profiles.get(
                    self.profile_name
                )
                if not isinstance(raw_profile, dict):
                    return empty_values
                storage = raw_profile.get("storage")
                if not isinstance(storage, dict):
                    return empty_values
                raw_drive = storage.get("google_drive")
                if not isinstance(raw_drive, dict):
                    return empty_values

                return _values_from_drive(raw_drive)
            except Exception:
                return empty_values

    def _db_google_profile_presence(self, profile_name: str) -> tuple[bool, bool]:
        """Return ``(auth_present, setup_present)`` for a Google Drive profile from
        the durable ``file_storage_profiles`` DB row — the SOLE home for the OAuth
        secrets after W28M-1605-FIX (config.yaml no longer stores them). Returns
        ``(False, False)`` when the DB or row is unavailable."""
        if self.db_runtime is None:
            return (False, False)
        try:
            with self.db_runtime.session_manager.session() as session:
                row = (
                    session.query(FileStorageProfile)
                    .filter_by(name=profile_name, is_active=True)
                    .first()
                )
                if row is None or not row.config_json:
                    return (False, False)
                cfg = json.loads(row.config_json)
                drive = ((cfg.get("storage") or {}).get("google_drive")) or {}
                if not isinstance(drive, dict):
                    return (False, False)
                auth_present = bool(drive.get("refresh_token") or drive.get("access_token"))
                setup_present = bool(
                    drive.get("client_id")
                    and drive.get("client_secret")
                    and (drive.get("folder_id") or drive.get("folder_url"))
                )
                return (auth_present, setup_present)
        except Exception:
            return (False, False)

    def _read_profile_metadata(self) -> dict[str, dict[str, Any]]:
        """Handle read profile metadata."""
        config_path_str = self.active_config
        if not path_utils.exists(config_path_str):
            return {}
        try:
            parsed = load_yaml(config_path_str, missing_ok=True)
        except Exception:
            return {}
        profiles = parsed.get("profiles")
        if not isinstance(profiles, dict):
            return {}
        summary: dict[str, dict[str, Any]] = {}
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            storage = profile.get("storage")
            backend = (
                ((storage or {}).get("backend")) if isinstance(storage, dict) else None
            )
            backend_name = str(backend or "unknown")
            metadata: dict[str, Any] = {
                "backend": backend_name,
                "google_auth_required": False,
            }
            if backend_name.strip().lower() in {
                "google_drive",
                "gdrive",
                "drive",
            } and isinstance(storage, dict):
                gcfg = storage.get("google_drive")
                if isinstance(gcfg, dict):
                    client_id = self._resolve_config_value(gcfg.get("client_id"))
                    client_secret = self._resolve_config_value(
                        gcfg.get("client_secret")
                    )
                    folder_id = self._resolve_config_value(gcfg.get("folder_id"))
                    folder_url = self._resolve_config_value(gcfg.get("folder_url"))
                    refresh_token = self._resolve_config_value(
                        gcfg.get("refresh_token")
                    )
                    access_token = self._resolve_config_value(gcfg.get("access_token"))
                    auth_present = bool(refresh_token or access_token)
                    setup_present = bool(
                        client_id and client_secret and (folder_id or folder_url)
                    )
                    # W28M-1605-FIX: OAuth secrets (refresh/access token,
                    # client_secret) live ONLY in the durable DB row now — never
                    # in config.yaml. Consult the DB so the status reflects the
                    # real credential state instead of falsely demanding re-auth.
                    db_auth, db_setup = self._db_google_profile_presence(str(name))
                    metadata["google_auth_required"] = not (auth_present or db_auth)
                    metadata["google_setup_present"] = setup_present or db_setup
            summary[str(name)] = metadata
        return summary

    def _build_root_summary(self) -> dict[str, Any]:
        """Handle build root summary."""
        profile_metadata = self._read_profile_metadata()
        profile_backends = {
            name: str(meta.get("backend", "unknown"))
            for name, meta in profile_metadata.items()
        }
        profile_health: dict[str, Any] = {}
        for name, backend in profile_backends.items():
            state = ENDPOINT_HEALTH_MANAGER.get_state(name, backend)
            if state is None:
                states_for_profile = ENDPOINT_HEALTH_MANAGER.get_profile_states(name)
                state = states_for_profile.get(backend) if states_for_profile else None
            if state is None:
                profile_health[name] = {
                    "backend": backend,
                    "status": "unknown",
                    "reason": "not_checked",
                    "requires_restart": False,
                    "signal": "red",
                }
                continue
            profile_health[name] = {
                "backend": state.backend,
                "status": state.status,
                "reason": state.reason,
                "requires_restart": state.requires_restart,
                "signal": "green" if state.status == "healthy" else "red",
            }
        return {
            "status": "ok",
            "service": self.app_name,
            "profile": self.profile_name,
            "transport": self.transport,
            "env_file": self.env_file,
            "config_path": self.active_config,
            "profiles": profile_backends,
            "profile_metadata": profile_metadata,
            "profile_health": profile_health,
            "mcp_endpoint": "/mcp",
            "health_endpoint": self.health_path,
        }

    def _render_root_summary_html(self, summary: dict[str, Any]) -> str:
        """Handle render root summary html."""
        profile_health = summary.get("profile_health") or {}
        profile_metadata = summary.get("profile_metadata") or {}

        def _action_cell(name: str) -> str:
            """Handle action cell."""
            metadata = profile_metadata.get(name) or {}
            requires_auth = bool(metadata.get("google_auth_required", False))
            health = profile_health.get(name) or {}
            health_auth_failed = (
                str(health.get("backend") or "").lower() == "google_drive"
                and str(health.get("status") or "").lower() == "auth_failed"
            )
            if not requires_auth and not health_auth_failed:
                return ""
            if not self.admin_ui_enabled:
                return "Enable admin UI to authorise"
            label = (
                "Re-authorise Google Drive"
                if health_auth_failed
                else "Authorise Google Drive"
            )
            return f"<a class='btn' href='/admin/google-drive?profile={escape(name)}'>{label}</a>"

        profile_rows = "".join(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f"<td>{escape(backend)}</td>"
            f"<td><span class='status-dot {escape(str((profile_health.get(name) or {}).get('signal', 'red')))}'></span> "
            f"{escape(str((profile_health.get(name) or {}).get('status', 'unknown')))}</td>"
            f"<td>{escape(str((profile_health.get(name) or {}).get('reason', 'not_checked')))}</td>"
            f"<td>{_action_cell(name)}</td>"
            "</tr>"
            for name, backend in sorted((summary.get("profiles") or {}).items())
        )
        if not profile_rows:
            profile_rows = (
                "<tr><td colspan='5'><em>No profiles discovered</em></td></tr>"
            )
        health_rows = "".join(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f"<td>{escape(str(state.get('backend', '')))}</td>"
            f"<td>{escape(str(state.get('status', '')))}</td>"
            f"<td>{escape(str(state.get('reason', '')))}</td>"
            "</tr>"
            for name, state in sorted(profile_health.items())
        )
        if not health_rows:
            health_rows = (
                "<tr><td colspan='4'><em>No endpoint-health state yet</em></td></tr>"
            )
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>file-mcp-server status</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;margin:20px;color:#111;}"
            "table{border-collapse:collapse;width:100%;max-width:980px;margin-bottom:18px;}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left;font-size:14px;}"
            "th{background:#f3f4f6;}"
            "code{background:#f3f4f6;padding:2px 4px;border-radius:3px;}"
            ".status-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle;}"
            ".status-dot.green{background:#15803d;}"
            ".status-dot.red{background:#b91c1c;}"
            ".btn{display:inline-block;padding:6px 10px;background:#0f766e;color:#fff;text-decoration:none;border-radius:4px;font-size:12px;}"
            "</style></head><body>"
            "<h1>file-mcp-server status</h1>"
            f"<p><strong>Profile:</strong> {escape(str(summary.get('profile')))}<br>"
            f"<strong>Transport:</strong> {escape(str(summary.get('transport')))}<br>"
            f"<strong>Env file:</strong> <code>{escape(str(summary.get('env_file') or ''))}</code><br>"
            f"<strong>Config:</strong> <code>{escape(str(summary.get('config_path') or ''))}</code><br>"
            f"<strong>MCP endpoint:</strong> <code>{escape(str(summary.get('mcp_endpoint') or '/mcp'))}</code><br>"
            f"<strong>Health endpoint:</strong> <code>{escape(str(summary.get('health_endpoint') or self.health_path))}</code></p>"
            "<h2>Configured Profiles</h2>"
            "<table><thead><tr><th>Profile</th><th>Backend</th><th>Signal</th><th>Reason</th><th>Action</th></tr></thead><tbody>"
            f"{profile_rows}</tbody></table>"
            "<h2>Endpoint Health (Per Profile)</h2>"
            "<table><thead><tr><th>Name</th><th>Backend</th><th>Status</th><th>Reason</th></tr></thead><tbody>"
            f"{health_rows}</tbody></table>"
            "</body></html>"
        )

    @staticmethod
    def _deep_copy_jsonish(value: Any) -> Any:
        """Clone a nested JSON-like structure."""
        return json.loads(json.dumps(value))

    def _merge_mapping(self, base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """Deep-merge mapping values recursively."""
        for key, value in patch.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._merge_mapping(base[key], value)
            else:
                base[key] = self._deep_copy_jsonish(value)
        return base

    def _compute_profile_status(
        self, *, backend: str, storage: dict[str, Any], roots: list[str]
    ) -> dict[str, Any]:
        """W28C-1702 (FM1): server-side 'configured' status for the SPA badge.

        Single source of truth computed from the DB-merged profile config per
        backend, replacing the SPA's broken single-profile ``backend_status``
        heuristic that rendered every non-local backend as ``not_configured``.
        Resolves ``${ENV}`` references and treats unresolved placeholders as
        absent. Returns ``status`` in {configured, partially_configured,
        not_configured} plus the list of ``missing`` required fields.
        """
        b = str(backend or "").strip().lower()
        storage = storage if isinstance(storage, dict) else {}

        def _missing(block_key: str, *fields: str) -> list[str]:
            block = storage.get(block_key)
            block = block if isinstance(block, dict) else {}
            return [f for f in fields if not self._configured_value(block.get(f))]

        if b == "local":
            required = ["roots"]
            missing = [] if roots else ["roots"]
        elif b == "s3":
            required = ["endpoint", "bucket", "access_key", "secret_key"]
            missing = _missing("s3", *required)
        elif b == "webdav":
            required = ["base_url", "username", "password"]
            missing = _missing("webdav", *required)
        elif b == "ftp":
            required = ["host", "username", "password"]
            missing = _missing("ftp", *required)
        elif b in {"google_drive", "gdrive", "drive"}:
            required = [
                "refresh_token",
                "folder_id",
                "user_email",
                "client_id",
                "client_secret",
            ]
            missing = _missing("google_drive", *required)
        else:
            required = []
            missing = []

        if not missing:
            status = "configured"
        elif required and len(missing) >= len(required):
            status = "not_configured"
        else:
            status = "partially_configured"
        return {"status": status, "missing": missing}

    def _profile_backend_health(
        self, *, profile_name: str, backend: str
    ) -> dict[str, Any] | None:
        backend_name = str(backend or "").strip().lower()
        state = ENDPOINT_HEALTH_MANAGER.get_state(profile_name, backend_name)
        if state is None:
            states = ENDPOINT_HEALTH_MANAGER.get_profile_states(profile_name)
            state = states.get(backend_name) if states else None
        if state is None:
            return None
        return {
            "backend": state.backend,
            "status": state.status,
            "reason": state.reason,
            "updated_at": state.updated_at,
            "requires_restart": state.requires_restart,
        }

    def _render_gdrive_status_banner(self, profile_name: str) -> str:
        """W28C-1702 (FM9): server-rendered banner reflecting the profile's
        google_drive DB state — the authoritative connection indicator (the
        admin form's localStorage prefill no longer fakes 'already connected').
        Computes the google_drive-block status regardless of the profile's
        declared backend, so the banner is honest for any selected profile.
        """
        storage: dict[str, Any] = {}
        for item in self._list_profile_payloads():
            if item.get("name") == profile_name:
                prof = item.get("profile") or {}
                storage = prof.get("storage") if isinstance(prof, dict) else {}
                break
        if not isinstance(storage, dict):
            storage = {}
        gd_status = self._compute_profile_status(
            backend="google_drive", storage=storage, roots=[]
        )
        status = gd_status["status"]
        missing = gd_status["missing"]
        health = self._profile_backend_health(
            profile_name=profile_name, backend="google_drive"
        )
        health_status = str((health or {}).get("status") or "").strip().lower()
        gd = storage.get("google_drive") if isinstance(storage, dict) else {}
        user_email = (
            self._configured_value((gd or {}).get("user_email"))
            if isinstance(gd, dict)
            else ""
        )
        if status == "configured" and health_status == "auth_failed":
            colour, label = "#b00020", "&#x1F534; RE-AUTHORISATION REQUIRED"
            who = f" for <b>{escape(user_email)}</b>" if user_email else ""
            detail = (
                f"Google Drive tokens exist for profile <b>{escape(profile_name)}</b>{who}, "
                "but the live OAuth refresh check failed. Submit the form below to replace "
                "the revoked or expired tokens."
            )
        elif status == "configured" and health_status and health_status != "healthy":
            colour, label = "#b07000", "&#x1F7E1; CHECK FAILED"
            detail = (
                f"Google Drive fields exist for profile <b>{escape(profile_name)}</b>, "
                f"but endpoint health is <code>{escape(health_status)}</code>. "
                "Submitting the form below re-authorises and replaces the stored tokens."
            )
        elif status == "configured":
            colour, label = "#0b8043", "&#x1F7E2; CONFIGURED"
            who = f" — last authorised <b>{escape(user_email)}</b>" if user_email else ""
            detail = (
                f"Google Drive is connected for profile <b>{escape(profile_name)}</b>{who}. "
                "Submitting the form below re-authorises and REPLACES the stored tokens."
            )
        elif status == "partially_configured":
            colour, label = "#b07000", "&#x1F7E1; PARTIALLY CONFIGURED"
            detail = (
                f"Profile <b>{escape(profile_name)}</b> is missing: "
                f"<code>{escape(', '.join(missing))}</code>. Complete the form to finish setup."
            )
        else:
            colour, label = "#b00020", "&#x1F534; NOT CONFIGURED"
            detail = (
                f"No captured Google Drive tokens for profile <b>{escape(profile_name)}</b>."
            )
        return (
            f'<div style="padding:10px 12px;margin:12px 0;border:1px solid {colour};'
            f'border-left:6px solid {colour};border-radius:4px;background:#fafafa;">'
            f'<div style="font-weight:700;color:{colour};">{label}</div>'
            f'<div style="font-size:0.95em;color:#333;">{detail}</div>'
            "</div>"
        )

    def _profile_payload(self, *, name: str, profile: dict[str, Any]) -> dict[str, Any]:
        """Normalise a profile entry for API/UI responses."""
        normalized_profile = _normalise_profile_mapping(
            profile,
            fallback_profile=(self.config.profiles.get(name) if self.config else None),
            default_profile=(self.config.profiles.get("default") if self.config else None),
        )
        storage = normalized_profile.get("storage") if isinstance(normalized_profile, dict) else {}
        scope = normalized_profile.get("scope") if isinstance(normalized_profile, dict) else {}
        auth = normalized_profile.get("auth") if isinstance(normalized_profile, dict) else {}
        backend = (
            str((storage or {}).get("backend") or "unknown")
            if isinstance(storage, dict)
            else "unknown"
        )
        roots = []
        if isinstance(scope, dict):
            roots = [str(item) for item in (scope.get("roots") or [])]
        api_keys = []
        if isinstance(auth, dict):
            api_keys = [str(item) for item in (auth.get("api_keys") or [])]
        # Platform-wide config-description rollout: first-class human
        # description sourced from the JSON store schema (config top-level key).
        # Pre-existing profiles without the key surface "" (additive, safe).
        description = ""
        if isinstance(normalized_profile, dict):
            description = str(normalized_profile.get("description") or "")
        # W28C-1702 (FM1): per-row 'configured' status so the SPA badge has a
        # server-computed single source of truth (was always not_configured).
        status_info = self._compute_profile_status(
            backend=backend,
            storage=storage if isinstance(storage, dict) else {},
            roots=roots,
        )
        endpoint_health = self._profile_backend_health(profile_name=name, backend=backend)
        health_status = str((endpoint_health or {}).get("status") or "").strip().lower()
        if (
            backend.strip().lower() in {"google_drive", "gdrive", "drive"}
            and status_info["status"] == "configured"
            and endpoint_health is not None
            and health_status != "healthy"
        ):
            marker = (
                "google_drive_reauthorisation_required"
                if health_status == "auth_failed"
                else "google_drive_endpoint_health_failed"
            )
            missing = list(status_info["missing"])
            if marker not in missing:
                missing.append(marker)
            status_info = {"status": "partially_configured", "missing": missing}
        return {
            "name": name,
            "description": description,
            "backend": backend,
            "roots": roots,
            "api_keys_count": len(api_keys),
            "status": status_info["status"],
            "status_missing": status_info["missing"],
            "endpoint_health": endpoint_health,
            "profile": normalized_profile,
        }

    def _list_profile_payloads(self) -> list[dict[str, Any]]:
        """Return all configured profiles from the database."""
        if self.db_runtime is None:
            return []
        payloads: list[dict[str, Any]] = []
        with self.db_runtime.session_manager.session() as session:
            rows = (
                session.query(FileStorageProfile)
                .filter_by(is_active=True)
                .order_by(FileStorageProfile.name)
                .all()
            )
            for row in rows:
                try:
                    config = json.loads(row.config_json) if row.config_json else {}
                except Exception:
                    config = {}
                # First-class description column is authoritative when the JSON
                # store schema lacks the key (older rows). Additive back-fill.
                if isinstance(config, dict) and not str(config.get("description") or ""):
                    row_description = str(getattr(row, "description", "") or "")
                    if row_description:
                        config["description"] = row_description
                payloads.append(self._profile_payload(name=row.name, profile=config))
        return payloads

    def _render_profiles_admin_html(self) -> str:
        """Render admin profile management page."""
        rows = []
        for item in self._list_profile_payloads():
            rows.append(
                "<tr>"
                f"<td>{escape(item['name'])}</td>"
                f"<td>{escape(str(item['backend']))}</td>"
                f"<td>{escape(', '.join(item['roots']) or '-')}</td>"
                f"<td>{escape(str(item['api_keys_count']))}</td>"
                "</tr>"
            )
        if not rows:
            rows.append("<tr><td colspan='4'><em>No profiles configured</em></td></tr>")
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>file-mcp profile admin</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;margin:20px;color:#111;}"
            "table{border-collapse:collapse;width:100%;max-width:980px;margin-bottom:18px;}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left;font-size:14px;}"
            "th{background:#f3f4f6;}"
            "code{background:#f3f4f6;padding:2px 4px;border-radius:3px;}"
            "</style></head><body>"
            "<h1>Profile Management</h1>"
            "<p>Use API endpoints <code>/admin/profiles</code> for create/update/delete.</p>"
            "<table><thead><tr><th>Profile</th><th>Backend</th><th>Roots</th><th>API keys</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
            "<p><a href='/'>Back to status</a></p>"
            "</body></html>"
        )

    def _render_identity_admin_html(self) -> str:
        """Render admin identity page for users/groups/api keys."""
        if self.admin_identity_service is None:
            return (
                "<!doctype html><html><body><h1>Identity Management</h1>"
                "<p>Admin identity service unavailable.</p></body></html>"
            )
        users = self.admin_identity_service.list_users()
        groups = self.admin_identity_service.list_groups()
        keys = self.admin_identity_service.list_api_keys(include_inactive=True)

        user_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('username') or ''))}</td>"
            f"<td>{escape(str(item.get('display_name') or ''))}</td>"
            f"<td>{escape(str(item.get('is_active')))}</td>"
            f"<td>{escape(', '.join(item.get('groups') or []))}</td>"
            "</tr>"
            for item in users
        ) or "<tr><td colspan='4'><em>No users</em></td></tr>"

        group_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('name') or ''))}</td>"
            f"<td>{escape(', '.join(item.get('roles') or []))}</td>"
            f"<td>{escape(', '.join(item.get('members') or []))}</td>"
            "</tr>"
            for item in groups
        ) or "<tr><td colspan='3'><em>No groups</em></td></tr>"

        key_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('id') or ''))}</td>"
            f"<td>{escape(str(item.get('user_id') or ''))}</td>"
            f"<td>{escape(str(item.get('label') or ''))}</td>"
            f"<td>{escape(', '.join(item.get('scopes') or []))}</td>"
            f"<td>{escape(str(item.get('is_active')))}</td>"
            "</tr>"
            for item in keys
        ) or "<tr><td colspan='5'><em>No API keys</em></td></tr>"

        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>file-mcp identity admin</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;margin:20px;color:#111;}"
            "table{border-collapse:collapse;width:100%;max-width:980px;margin-bottom:18px;}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left;font-size:14px;}"
            "th{background:#f3f4f6;}"
            "code{background:#f3f4f6;padding:2px 4px;border-radius:3px;}"
            "</style></head><body>"
            "<h1>Identity Management</h1>"
            "<p>Use API endpoints <code>/admin/users</code>, <code>/admin/groups</code>, and "
            "<code>/admin/api-keys</code> for mutations.</p>"
            "<h2>Users</h2>"
            "<table><thead><tr><th>Username</th><th>Display Name</th><th>Active</th><th>Groups</th></tr></thead><tbody>"
            + user_rows
            + "</tbody></table>"
            "<h2>Groups</h2>"
            "<table><thead><tr><th>Name</th><th>Roles</th><th>Members</th></tr></thead><tbody>"
            + group_rows
            + "</tbody></table>"
            "<h2>API Keys</h2>"
            "<table><thead><tr><th>ID</th><th>User ID</th><th>Label</th><th>Scopes</th><th>Active</th></tr></thead><tbody>"
            + key_rows
            + "</tbody></table>"
            "<p><a href='/'>Back to status</a></p>"
            "</body></html>"
        )

    def _resolve_jobs_runtime(
        self, *, profile_name: str | None
    ) -> FileMcpJobsRuntime | None:
        """Resolve jobs runtime for profile when jobs are enabled."""
        provider = self.jobs_runtime_provider
        if not callable(provider):
            return None
        return provider(profile_name)

    def _resolve_log_file_candidates(
        self,
        *,
        profile_name: str,
        log_type: str,
    ) -> list[Path]:
        """Return candidate log files for the selected profile and surface."""
        selected_type = str(log_type or "app").strip().lower() or "app"
        candidates: list[Path] = []
        seen: set[str] = set()

        def _add_candidate(raw_path: str | None) -> None:
            candidate = _normalize_optional_path(raw_path)
            if candidate is None:
                return
            rendered = str(candidate)
            if rendered in seen:
                return
            seen.add(rendered)
            candidates.append(candidate)

        profile = self.config.profiles.get(profile_name) if self.config else None
        fallback_profile = self.config.profiles.get(self.profile_name) if self.config else None
        log_config = getattr(self.config, "log", None)
        role_key_map = {
            "api": "api_server_log",
            "web": "web_server_log",
            "mcp": "mcp_server_log",
            "a2a": "a2a_server_log",
        }

        if selected_type == "audit":
            if profile is not None:
                _add_candidate(getattr(profile.audit, "log_path", None))
            if fallback_profile is not None:
                _add_candidate(getattr(fallback_profile.audit, "log_path", None))
            _add_candidate(getattr(log_config, "audit_log", None))
            _add_candidate("/data/audit/audit.jsonl")
            return candidates

        if selected_type in role_key_map:
            _add_candidate(getattr(log_config, role_key_map[selected_type], None))
        elif self.server_role in role_key_map:
            _add_candidate(getattr(log_config, role_key_map[self.server_role], None))

        if selected_type in {"app", "application", "server", "logs"}:
            _add_candidate(getattr(log_config, "app_log", None))
        if profile is not None:
            _add_candidate(getattr(profile.observability, "log_path", None))
        if fallback_profile is not None:
            _add_candidate(getattr(fallback_profile.observability, "log_path", None))
        _add_candidate("/workspace/logs/server.log")
        return candidates

    @staticmethod
    def _normalise_log_row(raw_line: str, *, log_type: str, source: str) -> dict[str, Any] | None:
        """Convert a log line into the stable JSON shape used by the web UI."""
        text = raw_line.strip()
        if not text:
            return None

        payload: dict[str, Any] | None = None
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            payload = decoded

        def _first_value(keys: tuple[str, ...]) -> str | None:
            if not isinstance(payload, dict):
                return None
            for key in keys:
                value = payload.get(key)
                if value is None:
                    continue
                if isinstance(value, (dict, list)):
                    return json.dumps(value, sort_keys=True)
                rendered = str(value).strip()
                if rendered:
                    return rendered
            return None

        timestamp = _first_value(
            ("timestamp", "@timestamp", "time", "ts", "created_at", "datetime")
        )
        if not timestamp:
            match = re.search(r"\d{4}-\d{2}-\d{2}[T ][0-9:.+\-Z]+", text)
            if match:
                timestamp = match.group(0)

        level = _first_value(("level", "severity", "levelname", "log_level", "lvl"))
        if not level:
            match = re.search(r"\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b", text)
            if match:
                level = match.group(1)

        message = _first_value(("message", "msg", "event", "detail"))
        if not message:
            message = text
        return {
            "timestamp": timestamp,
            "level": (level or "INFO").upper(),
            "message": message,
            "log_type": log_type,
            "source": source,
        }

    def _read_normalised_log_rows(
        self,
        *,
        profile_name: str,
        log_type: str,
        limit: int,
    ) -> tuple[Path | None, list[dict[str, Any]]]:
        """Read and normalise the newest log rows for the selected profile/surface."""
        bounded_limit = max(1, min(limit, 500))
        for candidate in self._resolve_log_file_candidates(
            profile_name=profile_name,
            log_type=log_type,
        ):
            try:
                if not candidate.exists() or not candidate.is_file():
                    continue
                with candidate.open("r", encoding="utf-8", errors="replace") as handle:
                    tail_lines = deque(handle, maxlen=bounded_limit)
            except OSError:
                continue

            rows = [
                row
                for row in (
                    self._normalise_log_row(
                        line,
                        log_type=log_type,
                        source=str(candidate),
                    )
                    for line in tail_lines
                )
                if row is not None
            ]
            return candidate, rows
        return None, []

    async def _handle_jobs_api(
        self,
        *,
        scope: dict[str, Any],
        headers: dict[str, str],
        path: str,
        send,
    ) -> bool:
        """Handle authenticated PS-75/PS-76 job query and control routes."""
        if scope.get("type") != "http":
            return False
        method = str(scope.get("method") or "").upper()
        if not (path == "/api/v1/jobs" or path.startswith("/api/v1/jobs/")
                or path == "/v1/jobs" or path.startswith("/v1/jobs/")):
            return False

        is_authenticated, is_admin, principal_id = await self._admin_gate(
            scope=scope, headers=headers
        )
        _auth_info, selected_profile = await self._authenticate_request(
            scope=scope, headers=headers
        )
        if not is_authenticated:
            await self._send_api_error(
                send,
                status=401,
                code="UNAUTHENTICATED",
                message="Unauthorised",
            )
            return True

        runtime = self._resolve_jobs_runtime(profile_name=selected_profile)
        if runtime is None:
            await self._send_api_error(
                send,
                status=503,
                code="SERVICE_UNAVAILABLE",
                message="Jobs runtime not enabled for selected profile",
            )
            return True

        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        if path in ("/api/v1/jobs", "/v1/jobs"):
            limit = _to_int((query.get("limit") or [100])[0], default=100)
            status = str((query.get("status") or [""])[0]).strip() or None
            session_id = str((query.get("session_id") or [""])[0]).strip() or None
            job_type = str((query.get("job_type") or [""])[0]).strip() or None
            await self._send_json(
                send,
                status=200,
                payload={
                    "ok": True,
                    "profile": selected_profile,
                    "server_id": runtime.server_id,
                    "queue_backend": runtime.backend_name,
                    "jobs": runtime.list_jobs(
                        limit=limit,
                        status=status,
                        session_id=session_id,
                        job_type=job_type,
                        user_id=None if is_admin else principal_id,
                    ),
                },
            )
            return True

        if path in ("/api/v1/jobs/queue/status", "/v1/jobs/queue/status"):
            await self._send_json(
                send,
                status=200,
                payload={
                    "ok": True,
                    "profile": selected_profile,
                    "server_id": runtime.server_id,
                    "queue_backend": runtime.backend_name,
                    "queue_status": runtime.queue_status(),
                },
            )
            return True

        segments = [segment for segment in path.split("/") if segment]
        if segments and segments[0] == "api":
            segments = segments[1:]
        if len(segments) == 3 and method == "GET":
            job_id = segments[2]
            payload = runtime.get_job(job_id)
            if payload is None:
                await self._send_api_error(
                    send,
                    status=404,
                    code="NOT_FOUND",
                    message=f"Job not found: {job_id}",
                )
                return True
            if not is_admin and str(payload.get("user_id") or "") != principal_id:
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message="Permission denied: job ownership required",
                )
                return True
            await self._send_json(send, status=200, payload={"ok": True, "job": payload})
            return True

        if len(segments) == 4 and method == "POST":
            job_id, action = segments[2], segments[3]
            payload = runtime.get_job(job_id)
            if payload is None:
                await self._send_api_error(
                    send, status=404, code="NOT_FOUND", message=f"Job not found: {job_id}"
                )
                return True
            owns_job = str(payload.get("user_id") or "") == principal_id
            if action in {"cancel", "retry"} and not (is_admin or owns_job):
                await self._send_api_error(
                    send, status=403, code="FORBIDDEN", message="Permission denied: job ownership required"
                )
                return True
            if action == "delete" and not is_admin:
                await self._send_api_error(
                    send, status=403, code="FORBIDDEN", message="Permission denied: admin required"
                )
                return True
            actions = {
                "cancel": (runtime.cancel, "cancelled"),
                "retry": (runtime.retry, "retried"),
                "delete": (runtime.archive, "deleted"),
            }
            selected = actions.get(action)
            if selected is None:
                await self._send_api_error(
                    send, status=404, code="NOT_FOUND", message="Not Found"
                )
                return True
            operation, response_key = selected
            changed = bool(operation(job_id))
            if not changed:
                await self._send_api_error(
                    send,
                    status=409,
                    code="CONFLICT",
                    message=f"Job is not eligible for {action}",
                )
                return True
            await self._send_json(
                send,
                status=200,
                payload={"ok": True, response_key: True, "job_id": job_id},
            )
            return True

        await self._send_api_error(
            send,
            status=404,
            code="NOT_FOUND",
            message="Not Found",
        )
        return True

    async def _handle_logs_api(
        self,
        *,
        scope: dict[str, Any],
        headers: dict[str, str],
        path: str,
        send,
    ) -> bool:
        """Handle read-only logs API routes."""
        if scope.get("type") != "http":
            return False
        method = str(scope.get("method") or "").upper()
        if path not in {"/api/v1/logs", "/v1/logs"}:
            return False

        supplied_admin_token = headers.get("x-admin-token", "")
        ui_admin = bool(self.admin_ui_token and supplied_admin_token == self.admin_ui_token)
        auth_info, selected_profile = await self._authenticate_request(
            scope=scope,
            headers=headers,
        )
        if not ui_admin and auth_info is None:
            await self._send_api_error(
                send,
                status=401,
                code="UNAUTHENTICATED",
                message="Unauthorised",
            )
            return True

        if method != "GET":
            await self._send_api_error(
                send,
                status=405,
                code="METHOD_NOT_ALLOWED",
                message=f"Unsupported method for {path}: {method}",
            )
            return True

        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        limit_value = (query.get("limit") or query.get("lines") or ["100"])[0]
        limit = _to_int(limit_value, default=100)
        log_type = str((query.get("type") or query.get("log_type") or ["app"])[0]).strip()
        selected_type = log_type.lower() or "app"
        log_path, rows = self._read_normalised_log_rows(
            profile_name=selected_profile,
            log_type=selected_type,
            limit=limit,
        )
        await self._send_json(
            send,
            status=200,
            payload={
                "ok": True,
                "profile": selected_profile,
                "log_type": selected_type,
                "log_path": str(log_path) if log_path is not None else None,
                "count": len(rows),
                "items": rows,
            },
        )
        return True

    async def __call__(self, scope, receive, send) -> None:
        """Handle callable invocation for this instance."""
        headers = {
            (k.decode("latin-1").lower() if isinstance(k, bytes) else str(k).lower()): (
                v.decode("latin-1") if isinstance(v, bytes) else str(v)
            )
            for k, v in (scope.get("headers") or [])
        }
        path = str(scope.get("path") or "")
        # W28A-876: the shared @cloud-dog/idam admin pages call
        # /api/v1/admin/<entity> (users/groups/api-keys/roles). Traefik strips the
        # /api prefix, so requests arrive here as /v1/admin/<entity> — a path the
        # canonical /admin/<entity> routing below does not match (→ 404, leaving
        # the shared pages unable to load data). Normalise the /v1 prefix away for
        # admin routes so the existing identity/admin dispatch resolves them.
        if path.startswith("/v1/admin/") or path == "/v1/admin":
            path = path[len("/v1"):]
        method = str(scope.get("method") or "").upper()
        accept = headers.get("accept", "")

        if scope.get("type") == "http" and method in {"GET", "HEAD"}:
            canonical_location = self._canonical_ui_redirect_location(
                path,
                scope.get("query_string", b""),
            )
            if canonical_location is not None:
                await self._send_redirect(
                    send,
                    location=canonical_location,
                    status=308,
                )
                return

        # Thread-a flat-role write-gate must fire before the generic
        # no-unguarded-route chokepoint so authenticated read-only users get
        # the explicit 403 read-only contract instead of a catalog 401/403.
        if scope.get("type") == "http" and method in {"POST", "PUT", "PATCH", "DELETE"}:
            _flat_gate_sess = self._get_session_from_cookie(headers)
            if (
                _flat_gate_sess is not None
                and not role_can_write(_flat_gate_sess.get("role"))
                and self._is_write_gated_data_path(path)
            ):
                await self._send_bytes(
                    send,
                    status=403,
                    body=json.dumps(
                        {
                            "detail": "read-only role: write operations are not permitted",
                            "role": FLAT_READ_ONLY_ROLE,
                        }
                    ).encode("utf-8"),
                    content_type="application/json",
                )
                return

        # ─── W28A-742 route-guard chokepoint ────────────────────────────────
        # Classify (method, path) against the file-mcp-local route catalog
        # (route_guards.classify). For "guarded" / "unknown" paths the guard
        # resolves the principal and calls
        # cloud_dog_idam.rbac.grants.authorise(...) — default-DENY. For
        # "public" / "auth" / "ui" / "idam_v1" paths the chokepoint passes
        # through to the existing dispatch unchanged. The IDAM-v1 surface
        # carries its own inline guards per the v3 comparison map §3.3.
        #
        # CFI: the chokepoint sits HERE (immediately after path/method
        # extraction) so that NO data/API/MCP/A2A/admin route can fire
        # before the guard decides. UI/static routes still resolve below
        # because the chokepoint returns False for "ui" classifications.
        # See the v3 comparison map §3.1 + W28A-742-COORDINATOR-MAP-V2
        # sendback §F4.
        try:
            from . import guard as _w28a742_guard

            if await _w28a742_guard.check_route_guard(
                self,
                scope,
                receive,
                send,
                method=method,
                path=path,
                headers=headers,
            ):
                # 401/403 already sent by the chokepoint.
                return
        except Exception:
            # The chokepoint MUST NOT crash the dispatcher. A bug inside
            # the chokepoint is logged downstream by the existing handlers
            # (which will then enforce their own auth as before).
            pass

        # ── W28E-1870-B storage change-watch REST surface (PS-102 §5.5) ──
        # /v1/watches* — create/list/status/events(get_batch)/ack/recover/
        # pause/resume/test-event/delete. Nonblocking pull-batch base mode
        # (CSTREAM-002). RBAC is enforced inside the handler via the
        # lightweight principal resolver; the chokepoint classifies these as
        # guarded and has already resolved/denied anonymous callers above.
        # The web role must proxy watches to the API role before considering the
        # local handler: the API role owns the process-shared watch service.
        if (
            scope.get("type") == "http"
            and self.server_role == "web"
            and self._is_watches_path(path)
            and await self._maybe_proxy_web_request(
                scope=scope,
                receive=receive,
                send=send,
                headers=headers,
                path=path,
                method=method,
                accept=accept,
            )
        ):
            return

        if scope.get("type") == "http" and self._is_watches_path(path):
            if await self._handle_watches(scope, receive, send, method=method, path=path, headers=headers):
                return

        # W28A-876: serve the canonical SHARED cloud_dog_idam /idam/v1 surface
        # (resource-registry + rbac-bindings) — the RBAC page calls /v1/idam/v1/<x>.
        # This integrates the ONE estate-wide implementation into the bespoke ASGI
        # dispatcher (file-mcp does not use FastAPI routing for the admin surface).
        #
        # W28A-742 (§3.3): extended with DB-backed POST / GET-by-id / DELETE on
        # ``/idam/v1/rbac/bindings`` (slash canonical) PLUS the back-compat
        # ``rbac-bindings`` hyphen alias. The 0.5.0 router's in-memory
        # ``_bindings: dict`` is NOT used; persistence goes through
        # ``RBACBindingRepository`` over file-mcp's session. The shim also
        # normalises ``/v1/idam/v1/...`` because the surrounding ``"/idam/v1/"
        # in path`` test matches BOTH prefixes (v3 §3.4.6).
        if scope.get("type") == "http" and "/idam/v1/" in path:
            _idam_sub = path.split("/idam/v1/", 1)[1].split("?", 1)[0]
            try:
                from cloud_dog_idam.api.fastapi.router import (
                    resource_registry as _idam_resource_registry,
                )

                # GET resource-registry stays anon-passthrough; the IDAM page
                # needs the schema regardless of principal.
                if method == "GET" and _idam_sub.startswith("resource-registry"):
                    _idam_payload = await _idam_resource_registry()
                    await self._send_bytes(
                        send,
                        status=200,
                        body=json.dumps(_idam_payload).encode("utf-8"),
                        content_type="application/json",
                    )
                    return

                # W28A-742: DB-backed RBAC bindings CRUD.
                _is_bindings = _idam_sub.startswith("rbac/bindings") or _idam_sub.startswith(
                    "rbac-bindings"
                )
                if _is_bindings:
                    handled = await self._w28a742_handle_rbac_bindings(
                        scope=scope,
                        receive=receive,
                        send=send,
                        method=method,
                        idam_sub=_idam_sub,
                        headers=headers,
                    )
                    if handled:
                        return
            except Exception:
                pass

        # W28A-889-A-R2: best-effort IDAM capability probe. Serve /auth/status (and its
        # /api/auth/status alias) BEFORE the /api proxy strips "/api" and forwards to the API
        # server (which has no such route -> 404). The shared @cloud-dog/idam Users page
        # surfaced that 404 as a "Not Found" banner. Returns the caller's real cookie-session
        # capability (200 authed, 401 unauthenticated) — never escalates.
        if scope.get("type") == "http" and method == "GET" and path in ("/auth/status", "/api/auth/status"):
            await self._handle_auth_status(send, headers, scope)
            return

        if scope.get("type") == "http" and method in {"POST", "PUT", "PATCH", "DELETE"}:
            _gate_sess = self._get_session_from_cookie(headers)
            if (
                _gate_sess is None
                and (path == self.mcp_path or path.startswith(f"{self.mcp_path.rstrip('/')}/"))
                and not (
                    headers.get("authorization", "").strip()
                    or headers.get("x-api-key", "").strip()
                )
            ):
                await self._send_bytes(
                    send,
                    status=401,
                    body=b'{"detail":"Not authenticated"}',
                    content_type="application/json",
                )
                return

        if await self._maybe_proxy_web_request(
            scope=scope,
            receive=receive,
            send=send,
            headers=headers,
            path=path,
            method=method,
            accept=accept,
        ):
            return

        if await self._handle_rest_file_lifecycle(
            scope=scope,
            receive=receive,
            send=send,
            headers=headers,
            path=path,
            method=method,
        ):
            return

        # Auth endpoints — handle before any other routing.
        if scope.get("type") == "http":
            if path == "/auth/login" and method == "POST":
                await self._handle_auth_login(receive, send, headers)
                return
            if path == "/auth/me" and method == "GET":
                await self._handle_auth_me(send, headers, scope)
                return
            if path == "/auth/logout" and method == "POST":
                await self._handle_auth_logout(send, headers)
                return

        # A2A agent card
        if scope.get("type") == "http" and method == "GET" and path == "/.well-known/agent.json":
            body = json.dumps(self._a2a_card).encode("utf-8")
            await self._send_bytes(send, status=200, body=body, content_type="application/json")
            return

        # A2A task submission
        if scope.get("type") == "http" and method == "POST" and path in ("/a2a/tasks", "/tasks"):
            body_chunks = []
            while True:
                message = await receive()
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            raw_body = b"".join(body_chunks)
            try:
                task_body = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                task_body = {}
            from uuid import uuid4 as _uuid4
            task_id = task_body.get("id", str(_uuid4()))
            skill_id = task_body.get("skill_id", "")
            _a2a_t0 = time.monotonic()
            if skill_id == "health":
                resp = {"id": task_id, "status": "completed", "output": {"type": "text", "text": "file-mcp is healthy"}}
            elif skill_id in self._a2a_skill_map:
                skill = self._a2a_skill_map[skill_id]
                input_data = task_body.get("input", {})
                input_text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)
                if skill.handler is not None:
                    try:
                        result = skill.handler(input_text)
                        import asyncio as _asyncio
                        if _asyncio.iscoroutine(result):
                            result = await result
                        resp = {"id": task_id, "status": "completed", "output": {"type": "text", "text": str(result)}}
                    except Exception as _exc:
                        resp = {"id": task_id, "status": "failed", "error": str(_exc)}
                else:
                    resp = {"id": task_id, "status": "completed", "output": {"type": "text", "text": f"Skill '{skill_id}' acknowledged (no handler configured)"}}
            else:
                resp = {"id": task_id, "status": "failed", "error": f"Unknown skill: {skill_id}. Available: {list(self._a2a_skill_map.keys())}"}
            _a2a_duration_ms = round((time.monotonic() - _a2a_t0) * 1000, 2)
            _a2a_input_data = task_body.get("input", {})
            _a2a_input_text = (
                _a2a_input_data.get("text", "")
                if isinstance(_a2a_input_data, dict)
                else str(_a2a_input_data)
            )
            self.logger.info(
                "a2a_task_execution",
                event_type="a2a_task",
                action=f"execute:{skill_id}",
                actor="a2a-caller",
                target=skill_id,
                outcome=resp.get("status", "unknown"),
                correlation_id=task_id,
                task_id=task_id,
                skill_id=skill_id,
                duration_ms=_a2a_duration_ms,
                input_length=len(_a2a_input_text),
            )
            body = json.dumps(resp).encode("utf-8")
            await self._send_bytes(send, status=200, body=body, content_type="application/json")
            return

        if scope.get("type") == "http" and method in {"GET", "HEAD"}:
            if path == "/runtime-config.js":
                await self._serve_runtime_config(send, method=method)
                return
            if path == "/version":
                # W28E-1863 fix-wave-b (WSC-014 / PS-30 UI-R7.3): expose source
                # commit + build date + deployment identity, not just version, so
                # the WebUI About page can render build provenance.
                _build = self._build_identity()
                payload = {
                    "version": self.version,
                    "service": "file-mcp-server",
                    "source_commit": _build["source_commit"],
                    "source_branch": _build["source_branch"],
                    "build_date": _build["build_date"],
                    "container_digest": _build["container_digest"],
                    "environment": _build["environment"],
                    # legacy field name the DashboardPage VersionInfo already reads
                    "commit": _build["source_commit"],
                }
                body = b"" if method == "HEAD" else json.dumps(payload).encode("utf-8")
                await self._send_bytes(
                    send,
                    status=200,
                    body=body,
                    content_type="application/json",
                )
                return
            if path == "/openapi.json":
                body = json.dumps(self._openapi_payload(), ensure_ascii=True).encode("utf-8")
                await self._send_bytes(
                    send, status=200, body=body, content_type="application/json"
                )
                return

            asset_path = self._resolve_ui_asset_path(path)
            if asset_path is not None:
                await self._send_file(send, path=asset_path, method=method)
                return

            if self._is_ui_route(path):
                # W28C-1702 (FM6): the google-drive setup SPA route is admin-only.
                # Deny anon BEFORE serving the shell (302→login for a browser,
                # 401 otherwise) so it matches the gated /admin/google-drive* APIs.
                if scope.get("type") == "http" and path == "/google-drive-settings":
                    _gd_authed, _gd_admin, _ = await self._admin_gate(
                        scope=scope, headers=headers
                    )
                    if not _gd_authed:
                        await self._deny_admin_access(send, headers=headers)
                        return
                admin_api_get_candidates = (
                    path == "/admin/users"
                    or path.startswith("/admin/users/")
                    or path == "/admin/groups"
                    or path.startswith("/admin/groups/")
                    or path == "/admin/api-keys"
                    or path.startswith("/admin/api-keys/")
                    or path == "/admin/roles"
                    or path.startswith("/admin/roles/")
                    or path == "/admin/profiles"
                    or path.startswith("/admin/profiles/")
                    or path == "/admin/runtime-config"
                    or path == "/admin/effective-config"
                )
                # Keep browser navigations on SPA routes while allowing API clients
                # (fetch/curl with non-HTML Accept) to hit JSON admin endpoints.
                if admin_api_get_candidates and "text/html" not in accept:
                    pass
                else:
                    await self._serve_spa_index(send, method=method)
                    return

        health_paths = {self.health_path}
        status_paths = {"/status"}
        health_base = self.health_path.rsplit("/", 1)[0] if "/" in self.health_path else ""
        if health_base:
            status_paths.add(f"{health_base}/status")
        ready_paths = {self._ready_path()}
        live_paths = {self._live_path()}
        if self.enable_legacy_api_alias:
            legacy_health = self._legacy_api_alias(self.health_path)
            legacy_ready = self._legacy_api_alias(self._ready_path())
            legacy_live = self._legacy_api_alias(self._live_path())
            legacy_root_health = self._legacy_root_alias(self.health_path)
            legacy_root_ready = self._legacy_root_alias(self._ready_path())
            legacy_root_live = self._legacy_root_alias(self._live_path())
            for status_path in tuple(status_paths):
                legacy_status = self._legacy_api_alias(status_path)
                legacy_root_status = self._legacy_root_alias(status_path)
                if legacy_status:
                    status_paths.add(legacy_status)
                if legacy_root_status:
                    status_paths.add(legacy_root_status)
            if legacy_health:
                health_paths.add(legacy_health)
            if legacy_ready:
                ready_paths.add(legacy_ready)
            if legacy_live:
                live_paths.add(legacy_live)
            if legacy_root_health:
                health_paths.add(legacy_root_health)
            if legacy_root_ready:
                ready_paths.add(legacy_root_ready)
            if legacy_root_live:
                live_paths.add(legacy_root_live)

        is_admin_route = path.startswith("/admin/")
        if await self._handle_jobs_api(scope=scope, headers=headers, path=path, send=send):
            return
        if await self._handle_logs_api(scope=scope, headers=headers, path=path, send=send):
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path in status_paths
        ):
            await self._send_json(send, status=200, payload=self._status_payload())
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path in health_paths
        ):
            body = json.dumps(self._health_response_payload()).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("utf-8")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and scope.get("path") == f"{self.mcp_path.rstrip('/')}/tools"
        ):
            auth_info, _selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            if auth_info is None:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return
            payload = self._list_tools_payload()
            body = json.dumps(payload).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and scope.get("path") == f"{self.web_mcp_path.rstrip('/')}/tools"
        ):
            auth_info, _selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            if auth_info is None:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return
            payload = self._list_tools_payload()
            body = json.dumps(payload).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        # W28A-742 (F-741-1 CLOSED): the unconditional ``/a2a/health`` 200
        # branch that lived here is DELETED. The route is now enforced by the
        # W28A-742 chokepoint at the top of ``__call__``: anon → 401; authed
        # principal with ``a2a.access`` → falls through to the A2A handler
        # below. PS-82 FR1.46: "GET /a2a/health without valid auth SHALL
        # return 401." See the W28A-742 comparison map §3.1.1.
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path == self.a2a_health_path
        ):
            auth_info, _selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            if auth_info is None:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return
            body = json.dumps(
                {
                    "status": "ok",
                    "service": "file-mcp-server",
                    "profile": self.profile_name,
                    "a2a": {"base_path": self.a2a_base_path},
                }
            ).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path in ready_paths
        ):
            readiness, checks = self._dependency_checks()
            body = json.dumps({"status": readiness, "checks": checks}).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path in live_paths
        ):
            body = json.dumps(
                {
                    "status": "ok",
                    "version": self.version,
                    "service": "file-mcp-server",
                }
            ).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        admin_api_path = path
        if path == "/api/admin" or path.startswith("/api/admin/"):
            admin_api_path = path[len("/api") :]
        elif path == "/v1/admin" or path.startswith("/v1/admin/"):
            admin_api_path = path[len("/v1") :]
        else:
            compact_identity_aliases = {
                "/v1/users": "/admin/users",
                "/v1/groups": "/admin/groups",
                "/v1/api-keys": "/admin/api-keys",
            }
            for compact_prefix, canonical_prefix in compact_identity_aliases.items():
                if path == compact_prefix or path.startswith(f"{compact_prefix}/"):
                    admin_api_path = f"{canonical_prefix}{path[len(compact_prefix):]}"
                    break
        is_identity_api_route = (
            admin_api_path == "/admin/users"
            or admin_api_path.startswith("/admin/users/")
            or admin_api_path == "/admin/groups"
            or admin_api_path.startswith("/admin/groups/")
            or admin_api_path == "/admin/api-keys"
            or admin_api_path.startswith("/admin/api-keys/")
            or admin_api_path == "/admin/roles"
            or admin_api_path.startswith("/admin/roles/")
        )
        is_profile_api_alias_route = admin_api_path == "/admin/profiles" or admin_api_path.startswith(
            "/admin/profiles/"
        )
        profile_api_path = admin_api_path if is_profile_api_alias_route else path
        is_runtime_config_api_route = path == "/admin/runtime-config"
        is_effective_config_api_route = path == "/admin/effective-config"
        is_profile_api_route = profile_api_path == "/admin/profiles" or profile_api_path.startswith(
            "/admin/profiles/"
        )
        is_profiles_html_request = (
            path == "/admin/profiles"
            and "text/html" in accept
            and "application/json" not in accept
        )
        is_webui_admin_route = (
            path == "/admin/identity"
            or is_profiles_html_request
            or path.startswith("/admin/google-drive")
        )
        requires_admin_ui_token_route = (
            path == "/admin/identity" or is_profiles_html_request
        )
        if scope.get("type") == "http" and is_admin_route:
            if is_webui_admin_route and not self.admin_ui_enabled:
                await self._send_api_error(
                    send, status=404, code="NOT_FOUND", message="Not Found"
                )
                return
            if (
                requires_admin_ui_token_route
                or (path == "/admin/reload" and self.admin_ui_enabled)
            ) and self.admin_ui_token:
                provided = headers.get("x-admin-token", "")
                if provided != self.admin_ui_token:
                    await self._send_api_error(
                        send,
                        status=401,
                        code="UNAUTHENTICATED",
                        message="Unauthorised",
                    )
                    return

        if (
            scope.get("type") == "http"
            and method == "GET"
            and is_profiles_html_request
        ):
            await self._send_html(send, status=200, html=self._render_profiles_admin_html())
            return

        if (
            scope.get("type") == "http"
            and method == "GET"
            and path == "/admin/identity"
        ):
            await self._send_html(send, status=200, html=self._render_identity_admin_html())
            return

        # /admin/google-drive/callback is the OAuth redirect target. Google redirects the
        # operator's browser here CROSS-SITE, so the admin session cookie is NOT sent — the
        # route therefore CANNOT be admin-gated (that returned UNAUTHENTICATED and blocked
        # Drive setup). Security is the OAuth `state` token: it is minted ONLY by the
        # admin-authed /start and tracked in `_oauth_state_principal`, so require a KNOWN
        # issued state here instead of the admin session. `complete_oauth_callback` then
        # further validates the pending state (single-use, expiry) and exchanges the code.
        if scope.get("type") == "http" and path == "/admin/google-drive/callback":
            _cb_query = parse_qs(
                scope.get("query_string", b"").decode("utf-8"),
                keep_blank_values=True,
            )
            _cb_state = (_cb_query.get("state") or [""])[0]
            if not _cb_state or _cb_state not in self._oauth_state_principal:
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message="Invalid or unknown OAuth state",
                )
                return
        # W28C-1702 (FM6): gate the other three google-drive admin surfaces with the
        # canonical admin check (the one /admin/profiles uses). These are reached directly
        # by the operator's browser WITH the admin session, so admin-gating them is correct.
        elif scope.get("type") == "http" and path in {
            "/admin/google-drive",
            "/admin/google-drive/start",
            "/google-drive-settings",
        }:
            gd_authenticated, gd_admin, gd_principal = await self._admin_gate(
                scope=scope, headers=headers
            )
            if not gd_authenticated:
                await self._deny_admin_access(send, headers=headers)
                return
            if not gd_admin:
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message="Missing permission: admin:google_drive",
                )
                return

        if scope.get("type") == "http" and (
            is_identity_api_route
            or is_profile_api_route
            or is_runtime_config_api_route
            or is_effective_config_api_route
        ):
            method = str(scope.get("method") or "GET").upper()
            supplied_admin_token = headers.get("x-admin-token", "")
            ui_admin = bool(
                self.admin_ui_token and supplied_admin_token == self.admin_ui_token
            )
            auth_info, selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            # Also accept cookie-based web UI sessions for admin identity routes
            cookie_session = self._get_session_from_cookie(headers)
            cookie_admin = cookie_session is not None and cookie_session.get("role") == "admin"
            scopes = self._token_scopes(auth_info)
            token_admin = self._has_admin_scope(scopes)
            is_authenticated = ui_admin or cookie_admin or auth_info is not None
            if not is_authenticated:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return
            if method != "GET" and not (ui_admin or cookie_admin or token_admin):
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message="Admin access required",
                )
                return

            try:
                if is_runtime_config_api_route:
                    if method != "GET":
                        await self._send_api_error(
                            send,
                            status=405,
                            code="METHOD_NOT_ALLOWED",
                            message=f"Unsupported method for {path}: {method}",
                        )
                        return
                    await self._send_json(
                        send,
                        status=200,
                        # W28C-1702 (FM2): mask storage secrets in the JSON dump.
                        payload=self._redact_profile_secrets(
                            self._admin_runtime_config_payload()
                        ),
                    )
                    return

                if is_effective_config_api_route:
                    if method != "GET":
                        await self._send_api_error(
                            send,
                            status=405,
                            code="METHOD_NOT_ALLOWED",
                            message=f"Unsupported method for {path}: {method}",
                        )
                        return
                    raw_query = scope.get("query_string") or b""
                    query = parse_qs(
                        raw_query.decode("utf-8", errors="ignore")
                        if isinstance(raw_query, (bytes, bytearray))
                        else str(raw_query)
                    )
                    reveal = str((query.get("reveal") or [""])[0]).lower() in {
                        "1",
                        "true",
                        "yes",
                    }
                    if reveal and not (ui_admin or cookie_admin or token_admin):
                        await self._send_api_error(
                            send,
                            status=403,
                            code="FORBIDDEN",
                            message="Admin access required to reveal secrets",
                        )
                        return
                    await self._send_json(
                        send,
                        status=200,
                        payload=self._effective_config_payload(reveal=reveal),
                    )
                    return

                routed_api_path = profile_api_path if is_profile_api_route else admin_api_path
                segments = [segment for segment in routed_api_path.split("/") if segment]

                if is_profile_api_route:
                    if method == "GET" and len(segments) == 2:
                        await self._send_json(
                            send,
                            status=200,
                            # W28C-1702 (FM2): mask storage secrets in the dump.
                            payload=self._redact_profile_secrets(
                                {"ok": True, "profiles": self._list_profile_payloads()}
                            ),
                        )
                        return

                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        profile_name = str(payload.get("name") or "").strip()
                        if not profile_name:
                            raise AdminIdentityError(
                                "VALIDATION_ERROR", "profile name is required"
                            )
                        if self.db_runtime is None:
                            raise AdminIdentityError(
                                "INTERNAL_ERROR", "database unavailable", status=500
                            )
                        with self.db_runtime.session_manager.session() as session:
                            stale_rows = (
                                session.query(FileStorageProfile)
                                .filter_by(name=profile_name, is_active=False)
                                .all()
                            )
                            for stale_row in stale_rows:
                                stale_row.name = _deleted_profile_name(profile_name)

                            existing = (
                                session.query(FileStorageProfile)
                                .filter_by(name=profile_name, is_active=True)
                                .first()
                            )
                            if existing is not None:
                                raise AdminIdentityError(
                                    "CONFLICT",
                                    f"profile already exists: {profile_name}",
                                    status=409,
                                )
                            if stale_rows:
                                session.commit()
                        profile_body = payload.get("profile")
                        if isinstance(profile_body, dict):
                            profile = self._deep_copy_jsonish(profile_body)
                        else:
                            profile = {
                                "auth": {"api_keys": []},
                                "storage": {"backend": "local"},
                                "scope": {"roots": []},
                            }
                            root = str(payload.get("root") or "").strip()
                            if root:
                                scope_cfg = profile.setdefault("scope", {})
                                scope_cfg["roots"] = [root]
                            backend = str(payload.get("backend") or "").strip()
                            if backend:
                                storage_cfg = profile.setdefault("storage", {})
                                storage_cfg["backend"] = backend
                            api_keys = [
                                str(item).strip()
                                for item in (payload.get("api_keys") or [])
                                if str(item).strip()
                            ]
                            if api_keys:
                                auth_cfg = profile.setdefault("auth", {})
                                auth_cfg["api_keys"] = api_keys
                        profile = _normalise_profile_mapping(
                            profile,
                            default_profile=(self.config.profiles.get("default") if self.config else None),
                        )
                        # Platform-wide config-description rollout: accept an
                        # optional human `description` on the profile. Persist it
                        # in BOTH the JSON store schema (top-level key on the
                        # config, survives normalisation) and the first-class
                        # column. Additive — omitting it defaults to "".
                        description = str(
                            payload.get("description")
                            if payload.get("description") is not None
                            else (profile.get("description") if isinstance(profile, dict) else "")
                        ).strip()
                        if isinstance(profile, dict):
                            profile["description"] = description
                        backend_value = "local"
                        if isinstance(profile.get("storage"), dict):
                            backend_value = str(profile["storage"].get("backend") or "local")
                        display_name = str(payload.get("display_name") or profile_name).strip()
                        new_row = FileStorageProfile(
                            id=f"prof_{uuid.uuid4().hex[:12]}",
                            name=profile_name,
                            display_name=display_name,
                            description=description,
                            backend=backend_value,
                            config_json=json.dumps(profile),
                            is_active=True,
                        )
                        with self.db_runtime.session_manager.session() as session:
                            session.add(new_row)
                            session.commit()
                        reload_result = None
                        if callable(self.reload_callback):
                            reload_result = self.reload_callback()
                        profile_payload = self._profile_payload(
                            name=profile_name,
                            profile=profile,
                        )
                        await self._publish_cfg_event(
                            resource="profile",
                            action="create",
                            identifier=str(profile_name),
                            after=dict(profile_payload) if isinstance(profile_payload, dict) else None,
                        )
                        await self._send_json(
                            send,
                            status=201,
                            payload={
                                "ok": True,
                                "profile": profile_payload,
                                "reloaded": bool(reload_result),
                                "reload": reload_result,
                            },
                        )
                        return

                    # W28C-1702 (FM2): owning-admin-only CLEARTEXT secret reveal
                    # (rotation workflows) with an audit trail; distinct from the
                    # redacted GET below.
                    if (
                        len(segments) == 4
                        and segments[3] == "secrets"
                        and method == "GET"
                    ):
                        _sr_authed, _sr_admin, _sr_principal = await self._admin_gate(
                            scope=scope, headers=headers
                        )
                        if not _sr_admin:
                            await self._send_api_error(
                                send,
                                status=403,
                                code="FORBIDDEN",
                                message="Admin access required",
                            )
                            return
                        sr_name = segments[2]
                        if self.db_runtime is None:
                            raise AdminIdentityError(
                                "INTERNAL_ERROR", "database unavailable", status=500
                            )
                        with self.db_runtime.session_manager.session() as session:
                            sr_row = (
                                session.query(FileStorageProfile)
                                .filter_by(name=sr_name, is_active=True)
                                .first()
                            )
                            if sr_row is None:
                                raise AdminIdentityError(
                                    "NOT_FOUND",
                                    f"unknown profile: {sr_name}",
                                    status=404,
                                )
                            try:
                                sr_profile = (
                                    json.loads(sr_row.config_json)
                                    if sr_row.config_json
                                    else {}
                                )
                            except Exception:
                                sr_profile = {}
                        self.logger.info(
                            "admin_secret_reveal",
                            extra={
                                "event_type": "admin.secret_reveal",
                                "actor": _sr_principal or "unknown",
                                "target": f"profile:{sr_name}",
                                "outcome": "ok",
                            },
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={
                                "ok": True,
                                "profile": self._profile_payload(
                                    name=sr_name, profile=sr_profile
                                ),
                            },
                        )
                        return

                    if len(segments) == 3:
                        profile_name = segments[2]
                        if self.db_runtime is None:
                            raise AdminIdentityError(
                                "INTERNAL_ERROR", "database unavailable", status=500
                            )
                        with self.db_runtime.session_manager.session() as session:
                            row = (
                                session.query(FileStorageProfile)
                                .filter_by(name=profile_name, is_active=True)
                                .first()
                            )
                            if row is None:
                                raise AdminIdentityError(
                                    "NOT_FOUND",
                                    f"unknown profile: {profile_name}",
                                    status=404,
                                )
                            try:
                                profile = json.loads(row.config_json) if row.config_json else {}
                            except Exception:
                                profile = {}
                            # First-class description column is authoritative
                            # when the JSON store schema lacks the key (older
                            # rows). Additive back-fill.
                            if isinstance(profile, dict) and not str(profile.get("description") or ""):
                                row_description = str(getattr(row, "description", "") or "")
                                if row_description:
                                    profile["description"] = row_description

                        if method == "GET":
                            await self._send_json(
                                send,
                                status=200,
                                # W28C-1702 (FM2): mask storage secrets in the dump.
                                payload=self._redact_profile_secrets({
                                    "ok": True,
                                    "profile": self._profile_payload(
                                        name=profile_name,
                                        profile=profile,
                                    ),
                                }),
                            )
                            return
                        if method in {"PUT", "PATCH"}:
                            payload = await self._read_json_body(receive)
                            candidate = self._deep_copy_jsonish(profile)
                            patch = payload.get("profile")
                            if isinstance(patch, dict):
                                self._merge_mapping(candidate, patch)
                            if "root" in payload:
                                root = str(payload.get("root") or "").strip()
                                candidate.setdefault("scope", {})["roots"] = (
                                    [root] if root else []
                                )
                            if "backend" in payload:
                                backend = str(payload.get("backend") or "").strip()
                                if backend:
                                    candidate.setdefault("storage", {})[
                                        "backend"
                                    ] = backend
                            if "api_keys" in payload:
                                api_keys = [
                                    str(item).strip()
                                    for item in (payload.get("api_keys") or [])
                                    if str(item).strip()
                                ]
                                candidate.setdefault("auth", {})["api_keys"] = api_keys
                            candidate = _normalise_profile_mapping(
                                candidate,
                                fallback_profile=(self.config.profiles.get(profile_name) if self.config else None),
                                default_profile=(self.config.profiles.get("default") if self.config else None),
                            )
                            backend_value = "local"
                            if isinstance(candidate.get("storage"), dict):
                                backend_value = str(candidate["storage"].get("backend") or "local")
                            display_name = str(payload.get("display_name") or "").strip()
                            # Platform-wide config-description rollout: allow the
                            # human `description` to be set/cleared on update.
                            # Only touched when the key is present so unrelated
                            # PATCHes preserve the existing description.
                            description_provided = "description" in payload
                            description = str(payload.get("description") or "").strip()
                            if isinstance(candidate, dict):
                                if description_provided:
                                    candidate["description"] = description
                                elif "description" not in candidate:
                                    candidate["description"] = ""
                            with self.db_runtime.session_manager.session() as session:
                                row = (
                                    session.query(FileStorageProfile)
                                    .filter_by(name=profile_name, is_active=True)
                                    .first()
                                )
                                if row is None:
                                    raise AdminIdentityError(
                                        "NOT_FOUND",
                                        f"unknown profile: {profile_name}",
                                        status=404,
                                    )
                                row.config_json = json.dumps(candidate)
                                row.backend = backend_value
                                if display_name:
                                    row.display_name = display_name
                                if description_provided:
                                    row.description = description
                                session.commit()
                            reload_result = None
                            if callable(self.reload_callback):
                                reload_result = self.reload_callback()
                            profile_payload_updated = self._profile_payload(
                                name=profile_name,
                                profile=candidate,
                            )
                            await self._publish_cfg_event(
                                resource="profile",
                                action="update",
                                identifier=str(profile_name),
                                after=dict(profile_payload_updated) if isinstance(profile_payload_updated, dict) else None,
                            )
                            await self._send_json(
                                send,
                                status=200,
                                payload={
                                    "ok": True,
                                    "profile": profile_payload_updated,
                                    "reloaded": bool(reload_result),
                                    "reload": reload_result,
                                },
                            )
                            return
                        if method == "DELETE":
                            if profile_name == selected_profile:
                                raise AdminIdentityError(
                                    "VALIDATION_ERROR",
                                    "cannot delete active profile",
                                )
                            with self.db_runtime.session_manager.session() as session:
                                row = (
                                    session.query(FileStorageProfile)
                                    .filter_by(name=profile_name, is_active=True)
                                    .first()
                                )
                                if row is None:
                                    raise AdminIdentityError(
                                        "NOT_FOUND",
                                        f"unknown profile: {profile_name}",
                                        status=404,
                                    )
                                row.name = _deleted_profile_name(profile_name)
                                row.is_active = False
                                session.commit()
                            reload_result = None
                            if callable(self.reload_callback):
                                reload_result = self.reload_callback()
                            await self._publish_cfg_event(
                                resource="profile",
                                action="delete",
                                identifier=str(profile_name),
                            )
                            await self._send_json(
                                send,
                                status=200,
                                payload={
                                    "ok": True,
                                    "deleted": True,
                                    "name": profile_name,
                                    "reloaded": bool(reload_result),
                                    "reload": reload_result,
                                },
                            )
                            return

                    await self._send_api_error(
                        send,
                        status=405,
                        code="METHOD_NOT_ALLOWED",
                        message=f"Unsupported method for {path}: {method}",
                    )
                    return

                if self.admin_identity_service is None:
                    await self._send_api_error(
                        send,
                        status=501,
                        code="INTERNAL_ERROR",
                        message="Admin identity service unavailable",
                    )
                    return

                service = self.admin_identity_service
                if len(segments) >= 2 and segments[1] == "users":
                    if method == "GET" and len(segments) == 2:
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "users": service.list_users()},
                        )
                        return
                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        display_name = str(
                            payload.get("display_name")
                            if payload.get("display_name") is not None
                            else payload.get("name") or ""
                        )
                        if "is_active" in payload:
                            is_active = bool(payload.get("is_active"))
                        elif "disabled" in payload:
                            is_active = not bool(payload.get("disabled"))
                        else:
                            is_active = True
                        created = service.create_user(
                            username=str(payload.get("username") or ""),
                            display_name=display_name,
                            is_active=is_active,
                            groups=payload.get("groups") or [],
                        )
                        await self._publish_cfg_event(
                            resource="user",
                            action="create",
                            identifier=str(
                                created.get("id") or created.get("user_id") or ""
                            ),
                            after=dict(created),
                        )
                        await self._send_json(
                            send,
                            status=201,
                            payload={"ok": True, "user": created},
                        )
                        return
                    if len(segments) == 3 and method == "GET":
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "user": service.get_user(segments[2])},
                        )
                        return
                    if len(segments) == 3 and method in {"PUT", "PATCH"}:
                        payload = await self._read_json_body(receive)
                        update_payload = dict(payload)
                        if "name" in update_payload and "display_name" not in update_payload:
                            update_payload["display_name"] = update_payload.get("name")
                        if "disabled" in update_payload and "is_active" not in update_payload:
                            update_payload["is_active"] = not bool(update_payload.get("disabled"))
                        if isinstance(update_payload.get("groups"), str):
                            update_payload["groups"] = [
                                item.strip()
                                for item in str(update_payload.get("groups") or "").split(",")
                                if item.strip()
                            ]
                        updated = service.update_user(segments[2], data=update_payload)
                        await self._publish_cfg_event(
                            resource="user",
                            action="update",
                            identifier=str(segments[2]),
                            after=dict(updated),
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "user": updated},
                        )
                        return
                    if len(segments) == 3 and method == "DELETE":
                        deleted = service.delete_user(segments[2])
                        await self._publish_cfg_event(
                            resource="user",
                            action="delete",
                            identifier=str(segments[2]),
                            before=dict(deleted) if isinstance(deleted, dict) else None,
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "result": deleted},
                        )
                        return

                if len(segments) >= 2 and segments[1] == "groups":
                    if method == "GET" and len(segments) == 2:
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "groups": service.list_groups()},
                        )
                        return
                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        created = service.create_group(
                            name=str(payload.get("name") or ""),
                            description=str(payload.get("description") or ""),
                            roles=payload.get("roles") or [],
                            is_active=bool(payload.get("is_active", True)),
                        )
                        await self._publish_cfg_event(
                            resource="group",
                            action="create",
                            identifier=str(
                                created.get("id") or created.get("group_id") or ""
                            ),
                            after=dict(created),
                        )
                        await self._send_json(
                            send,
                            status=201,
                            payload={"ok": True, "group": created},
                        )
                        return
                    if len(segments) == 3 and method == "GET":
                        await self._send_json(
                            send,
                            status=200,
                            payload={
                                "ok": True,
                                "group": service.get_group(segments[2]),
                            },
                        )
                        return
                    if len(segments) == 3 and method in {"PUT", "PATCH"}:
                        payload = await self._read_json_body(receive)
                        updated = service.update_group(segments[2], data=payload)
                        await self._publish_cfg_event(
                            resource="group",
                            action="update",
                            identifier=str(segments[2]),
                            after=dict(updated),
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "group": updated},
                        )
                        return
                    if len(segments) == 3 and method == "DELETE":
                        deleted = service.delete_group(segments[2])
                        await self._publish_cfg_event(
                            resource="group",
                            action="delete",
                            identifier=str(segments[2]),
                            before=dict(deleted) if isinstance(deleted, dict) else None,
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "result": deleted},
                        )
                        return

                if len(segments) >= 2 and segments[1] == "api-keys":
                    if method == "GET" and len(segments) == 2:
                        query = parse_qs(
                            scope.get("query_string", b"").decode("utf-8")
                        )
                        include_flag = str(
                            (query.get("include_inactive") or ["false"])[0]
                        ).strip()
                        include_inactive = (
                            include_flag.lower()
                            in {"1", "true", "yes"}
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={
                                "ok": True,
                                "api_keys": service.list_api_keys(
                                    include_inactive=include_inactive
                                ),
                            },
                        )
                        return
                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        created = service.create_api_key(
                            user_id=str(payload.get("user_id") or ""),
                            label=str(payload.get("label") or ""),
                            scopes=payload.get("scopes") or [],
                            profile_name=str(payload.get("profile_name") or ""),
                        )
                        await self._publish_cfg_event(
                            resource="api_key",
                            action="create",
                            identifier=str(
                                created.get("id") or created.get("api_key_id") or ""
                            ),
                            after=dict(created),
                        )
                        await self._send_json(
                            send,
                            status=201,
                            payload={"ok": True, "api_key": created},
                        )
                        return
                    if len(segments) == 4 and segments[3] == "revoke" and method == "POST":
                        revoked = service.revoke_api_key(segments[2])
                        await self._publish_cfg_event(
                            resource="api_key",
                            action="revoke",
                            identifier=str(segments[2]),
                            before=dict(revoked) if isinstance(revoked, dict) else None,
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "api_key": revoked},
                        )
                        return

                if len(segments) >= 2 and segments[1] == "roles":
                    if method == "GET" and len(segments) == 2:
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "roles": service.list_roles()},
                        )
                        return
                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        created = service.create_role(
                            name=str(payload.get("name") or ""),
                            description=str(payload.get("description") or ""),
                            permissions=payload.get("permissions") or [],
                        )
                        await self._publish_cfg_event(
                            resource="role",
                            action="create",
                            identifier=str(created.get("role_id") or ""),
                            after=dict(created),
                        )
                        await self._send_json(
                            send,
                            status=201,
                            payload={"ok": True, "role": created},
                        )
                        return
                    if len(segments) == 3 and method == "GET":
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "role": service.get_role(segments[2])},
                        )
                        return
                    if len(segments) == 3 and method in {"PUT", "PATCH"}:
                        payload = await self._read_json_body(receive)
                        updated = service.update_role(segments[2], data=payload)
                        await self._publish_cfg_event(
                            resource="role",
                            action="update",
                            identifier=str(segments[2]),
                            after=dict(updated),
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "role": updated},
                        )
                        return
                    if len(segments) == 3 and method == "DELETE":
                        deleted = service.delete_role(segments[2])
                        await self._publish_cfg_event(
                            resource="role",
                            action="delete",
                            identifier=str(segments[2]),
                            before=dict(deleted) if isinstance(deleted, dict) else None,
                        )
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "result": deleted},
                        )
                        return

                await self._send_api_error(
                    send,
                    status=405,
                    code="METHOD_NOT_ALLOWED",
                    message=f"Unsupported method for {path}: {method}",
                )
                return
            except AdminIdentityError as exc:
                await self._send_api_error(
                    send,
                    status=exc.status,
                    code=exc.code,
                    message=str(exc),
                )
                return
            except Exception as exc:
                await self._send_api_error(
                    send,
                    status=500,
                    code="INTERNAL_ERROR",
                    message=str(exc),
                )
                return

        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == "/admin/google-drive"
        ):
            callback_url = self._compute_callback_url(scope, headers)
            query = parse_qs(
                scope.get("query_string", b"").decode("utf-8"), keep_blank_values=True
            )
            selected_profile = (query.get("profile") or [""])[0].strip()
            lock_profile = bool(selected_profile)
            available_profiles = self.profile_names or [self.profile_name]
            prefill_profile = (
                selected_profile
                if selected_profile in available_profiles
                else (
                    available_profiles[0] if available_profiles else self.profile_name
                )
            )
            prefill_values = self._load_google_profile_values(
                profile_name=prefill_profile, callback_url=callback_url
            )
            html = render_setup_page(
                callback_url=callback_url,
                profiles=available_profiles,
                selected_profile=selected_profile,
                lock_profile=lock_profile,
                status_message="",
                prefills={
                    "user_email": prefill_values.get("user_email", ""),
                    "folder_input": prefill_values.get("folder_input", ""),
                    "client_id": prefill_values.get("client_id", ""),
                    "redirect_uri": prefill_values.get("redirect_uri", ""),
                    "token_uri": prefill_values.get("token_uri", ""),
                    "oauth_scope": prefill_values.get("oauth_scope", ""),
                    "oauth_authorize_uri": prefill_values.get(
                        "oauth_authorize_uri", ""
                    ),
                    "api_base_uri": prefill_values.get("api_base_uri", ""),
                    "folder_url_example": prefill_values.get("folder_url_example", ""),
                },
                has_client_secret=bool(prefill_values.get("client_secret", "")),
                folder_url_example=prefill_values.get("folder_url_example", ""),
                status_banner=self._render_gdrive_status_banner(prefill_profile),
            )
            await self._send_html(send, status=200, html=html)
            return
        if (
            scope.get("type") == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/admin/google-drive/start"
        ):
            body = await self._read_http_body(receive)
            try:
                data = parse_form_urlencoded(body)
                callback_uri = (data.get("redirect_uri") or "").strip()
                if not callback_uri:
                    callback_uri = self._compute_callback_url(scope, headers)
                profile_name = (data.get("profile") or "").strip() or self.profile_name
                stored_values = self._load_google_profile_values(
                    profile_name=profile_name,
                    callback_url=callback_uri,
                )

                client_secret = (data.get("client_secret") or "").strip()
                if not client_secret or client_secret == MASKED_CLIENT_SECRET:
                    data["client_secret"] = stored_values.get("client_secret", "")
                if not (data.get("client_id") or "").strip():
                    data["client_id"] = stored_values.get("client_id", "")
                if not (data.get("folder_input") or "").strip():
                    data["folder_input"] = stored_values.get("folder_input", "")
                if not (data.get("user_email") or "").strip():
                    data["user_email"] = stored_values.get("user_email", "")
                if not (data.get("redirect_uri") or "").strip():
                    data["redirect_uri"] = stored_values.get("redirect_uri", "")
                if (data.get("redirect_uri") or "").strip().lower() == OOB_REDIRECT_URI:
                    data["redirect_uri"] = callback_uri
                if not (data.get("token_uri") or "").strip():
                    data["token_uri"] = stored_values.get("token_uri", "")
                if not (data.get("oauth_scope") or "").strip():
                    data["oauth_scope"] = stored_values.get("oauth_scope", "")
                if not (data.get("oauth_authorize_uri") or "").strip():
                    data["oauth_authorize_uri"] = stored_values.get(
                        "oauth_authorize_uri", ""
                    )
                if not (data.get("api_base_uri") or "").strip():
                    data["api_base_uri"] = stored_values.get("api_base_uri", "")

                self.logger.info(
                    "admin_google_drive_start",
                    extra={
                        "profile": profile_name,
                        "callback_uri": callback_uri,
                        "has_client_id": bool((data.get("client_id") or "").strip()),
                        "has_client_secret": bool(
                            (data.get("client_secret") or "").strip()
                        ),
                    },
                )
                location = begin_oauth(data)
                # W28C-1702 (FM6): bind the issued OAuth `state` to the principal
                # that started the flow so /callback can reject a replayed state.
                _start_state = (
                    parse_qs(urlsplit(location).query).get("state") or [""]
                )[0]
                if _start_state:
                    _, _, _start_principal = await self._admin_gate(
                        scope=scope, headers=headers
                    )
                    self._oauth_state_principal[_start_state] = _start_principal
                if "application/json" in headers.get("accept", "").lower():
                    await self._send_json(
                        send,
                        status=200,
                        payload={"ok": True, "location": location},
                    )
                    return
                await self._send_redirect(send, location=location)
                return
            except Exception as exc:
                self.logger.exception(
                    "admin_google_drive_start_failed",
                    extra={"error": str(exc)},
                )
                html = render_setup_page(
                    callback_url="",
                    profiles=self.profile_names or [self.profile_name],
                    status_message=f"Failed to start OAuth flow: {exc}",
                    status_type="warn",
                )
                await self._send_html(send, status=400, html=html)
                return
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == "/admin/google-drive/callback"
        ):
            query = parse_qs(
                scope.get("query_string", b"").decode("utf-8"), keep_blank_values=True
            )
            state = (query.get("state") or [""])[0]
            code = (query.get("code") or [""])[0]
            oauth_error = (query.get("error") or [""])[0]
            oauth_error_description = (query.get("error_description") or [""])[0]
            if not state or not code:
                self.logger.warning(
                    "admin_google_drive_callback_missing_code_or_state",
                    extra={
                        "error": oauth_error,
                        "error_description": oauth_error_description,
                        "has_state": bool(state),
                        "has_code": bool(code),
                    },
                )
                await self._send_html(
                    send, status=400, html="<h1>Missing state or code in callback.</h1>"
                )
                return
            try:
                callback_fn = _resolve_complete_oauth_callback()
                # W28C-1702 (FM8): pass the DB session manager + the
                # FileStorageProfile model + reload_callback so captured OAuth
                # tokens persist to the file_storage_profiles row (durable on the
                # /workspace volume) instead of only to /app/config.yaml
                # (ephemeral, lost on container recreate).
                db_session_manager = None
                if self.db_runtime is not None:
                    db_session_manager = self.db_runtime.session_manager
                result = callback_fn(
                    state=state,
                    code=code,
                    config_path=path_utils.as_path(path_utils.resolve_path(self.active_config)),
                    db_session_manager=db_session_manager,
                    file_storage_profile_model=FileStorageProfile,
                    reload_callback=self.reload_callback
                    if self.admin_apply_on_callback and callable(self.reload_callback)
                    else None,
                )
                # complete_oauth_callback already triggers reload_callback when DB
                # args are supplied; this block narrates the durability outcome.
                if result.db_row_id is not None:
                    reload_message = (
                        f"Persisted to DB row {result.db_row_id}; config "
                        "hot-reloaded; survives container recreate."
                    )
                elif self.admin_apply_on_callback and callable(self.reload_callback):
                    try:
                        reload_info = self.reload_callback()
                        reload_message = (
                            "Config hot-reloaded for profile "
                            f"{reload_info.get('profile', self.profile_name)}; "
                            "NOTE: this run did NOT persist to DB — tokens are in "
                            "/app/config.yaml only and WILL be lost on container "
                            "recreate. Investigate db_runtime availability."
                        )
                    except Exception as exc:
                        reload_message = f"Config written but hot-reload failed: {exc}"
                else:
                    reload_message = "Restart server to apply updated config."
                # Styled, platform-consistent success page. Internal detail
                # (config.yaml path, DB row id, durability narration) is logged
                # server-side for audit but NEVER rendered to the user.
                html = render_link_success_page(
                    result,
                    continue_url="/admin/google-drive",
                    persisted=result.db_row_id is not None,
                )
                self.logger.info(
                    "admin_google_drive_callback_success",
                    extra={
                        "profile": result.profile,
                        "folder_id": result.folder_id,
                        "config_path": result.config_path,
                        "db_row_id": result.db_row_id,
                        "reload_message": reload_message,
                    },
                )
                await self._send_html(send, status=200, html=html)
                return
            except Exception as exc:
                self.logger.exception(
                    "admin_google_drive_callback_failed",
                    extra={"state": state, "error": str(exc)},
                )
                await self._send_html(
                    send,
                    status=400,
                    html=f"<h1>OAuth callback failed</h1><pre>{exc}</pre>",
                )
                return
        if (
            scope.get("type") == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/admin/reload"
        ):
            if not callable(self.reload_callback):
                await self._send_api_error(
                    send,
                    status=501,
                    code="INTERNAL_ERROR",
                    message="Reload callback not configured",
                )
                return
            try:
                result = self.reload_callback()
                body = json.dumps({"ok": True, "result": result}).encode("utf-8")
                await self._send_bytes(
                    send, status=200, body=body, content_type="application/json"
                )
                return
            except Exception as exc:
                await self._send_api_error(
                    send,
                    status=500,
                    code="INTERNAL_ERROR",
                    message=str(exc),
                )
                return

        # W28E-1863 fix-wave-b (CC-401): SPA deep-link fallback of LAST RESORT.
        # A browser hard-navigation / refresh / bookmark of a React history route
        # that is NOT in the enumerated ``_ui_route_paths`` allowlist (e.g. bare
        # ``/admin``, ``/system/preferences``, ``/research``) previously fell through
        # to the inner ASGI app below and returned a raw 404 JSON body instead of the
        # SPA shell. Serve index.html for any GET/HEAD document navigation to a
        # non-reserved, extensionless path so React renders the requested route — or,
        # for an anonymous visitor, its own login gate — instead of a raw error.
        #
        # This sits at the VERY END of dispatch, AFTER every explicit
        # API / MCP / A2A / health / auth / admin-gate / asset handler has already had
        # its chance to ``return``. So it can NEVER shadow those surfaces (the failure
        # mode of the reverted, Accept-driven mid-flow fix-wave-a, smoke PDS-007): an
        # unauthenticated API path (``/api/...``, ``/admin/users`` with a JSON Accept,
        # ``/google-drive-settings`` non-browser) has already been answered with its
        # 401 JSON above and never reaches here — the FM6 OAuth-leak contract is
        # untouched. Matches chat-client ``is_spa_document_navigation`` (2156ef9) +
        # sql-agent / search-mcp catch-all (AGENT-LESSONS §2.4).
        if (
            scope.get("type") == "http"
            and method in {"GET", "HEAD"}
            and is_spa_document_navigation(path)
        ):
            await self._serve_spa_index(send, method=method)
            return

        await self.app(scope, receive, send)


class StreamableHttpAcceptCompatibilityMiddleware:
    """Normalize Accept header for clients that only advertise JSON."""

    def __init__(self, app, *, mcp_path: str) -> None:
        """Initialise the instance state."""
        self.app = app
        self.mcp_path = mcp_path

    @staticmethod
    def _text(value: bytes | str) -> str:
        """Handle text."""
        if isinstance(value, bytes):
            return value.decode("latin-1")
        return str(value)

    async def __call__(self, scope, receive, send) -> None:
        """Handle callable invocation for this instance."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        if (
            str(scope.get("path") or "") != self.mcp_path
            or str(scope.get("method") or "").upper() != "POST"
        ):
            await self.app(scope, receive, send)
            return

        headers = list(scope.get("headers") or [])
        accept_idx: int | None = None
        accept_value = ""
        for idx, (key, value) in enumerate(headers):
            if self._text(key).lower() == "accept":
                accept_idx = idx
                accept_value = self._text(value)
                break

        normalized = accept_value.lower()
        has_json = "application/json" in normalized or "*/*" in normalized
        has_stream = "text/event-stream" in normalized or "*/*" in normalized
        if has_json and has_stream:
            await self.app(scope, receive, send)
            return

        patched_accept = accept_value.strip()
        if not patched_accept:
            patched_accept = "application/json, text/event-stream"
        else:
            if not has_json:
                patched_accept = f"{patched_accept}, application/json"
            if not has_stream:
                patched_accept = f"{patched_accept}, text/event-stream"

        patched_scope = dict(scope)
        patched_headers = list(headers)
        if accept_idx is None:
            patched_headers.append((b"accept", patched_accept.encode("latin-1")))
        else:
            key, _ = patched_headers[accept_idx]
            patched_headers[accept_idx] = (key, patched_accept.encode("latin-1"))
        patched_scope["headers"] = patched_headers
        await self.app(patched_scope, receive, send)


class RequestContextMiddleware:
    """Capture request context for per-tool operational logging."""

    def __init__(self, app) -> None:
        """Initialise the instance state."""
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        """Handle callable invocation for this instance."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            (
                key.decode("latin-1").lower()
                if isinstance(key, bytes)
                else str(key).lower()
            ): (value.decode("latin-1") if isinstance(value, bytes) else str(value))
            for key, value in (scope.get("headers") or [])
        }
        correlation_id = (
            headers.get("x-session-id")
            or headers.get("x-request-id")
            or uuid.uuid4().hex
        )
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        session_id = headers.get("x-session-id") or correlation_id
        client = scope.get("client")
        client_ip = (
            str(client[0]) if isinstance(client, tuple) and len(client) > 0 else None
        )
        # Extract profile from header or query parameter and set in context.
        # This allows the auth verifier to resolve the correct profile even
        # when called through FastMCP's single-token verify_token() path.
        profile_header = headers.get("x-file-mcp-profile", "")
        query_string = scope.get("query_string", b"")
        if isinstance(query_string, bytes):
            query_string = query_string.decode("latin-1", errors="replace")
        profile_query = ""
        for pair in query_string.split("&"):
            if pair.startswith("profile="):
                profile_query = pair.split("=", 1)[1]
                break
        request_profile = profile_header or profile_query or ""
        if request_profile:
            set_request_profile_name(request_profile)

        session_token = _REQUEST_SESSION_ID.set(session_id)
        client_ip_token = _REQUEST_CLIENT_IP.set(client_ip)
        set_api_kit_request_id(request_id)
        set_api_kit_correlation_id(correlation_id)
        set_correlation_id(correlation_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _REQUEST_SESSION_ID.reset(session_token)
            _REQUEST_CLIENT_IP.reset(client_ip_token)
            clear_correlation_id()


def _to_bool(value: Any, default: bool) -> bool:
    """Handle to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _to_int(value: Any, default: int) -> int:
    """Handle to int."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _normalize_path(path: str | None, *, default: str) -> str:
    """Handle normalize path."""
    if not path:
        return default
    cleaned = path.strip()
    if not cleaned:
        return default
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    if len(cleaned) > 1 and cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/")
    return cleaned or "/"


def _join_paths(base_path: str, path: str) -> str:
    """Handle join paths."""
    base = _normalize_path(base_path, default="/")
    sub = _normalize_path(path, default="/")
    if base == "/":
        return sub
    if sub == "/":
        return base
    return f"{base}{sub}"


def resolve_http_settings(http_config: HttpServerConfig) -> HttpRuntimeSettings:
    """Execute resolve http settings."""
    transport = (http_config.transport or "streamable-http").strip().lower()
    if transport not in {"streamable-http", "sse", "http"}:
        transport = "streamable-http"

    base_path = _normalize_path(http_config.base_path, default="/")
    # Canonical contract keeps MCP at an independent path (`/mcp`) while API
    # readiness/health/events may be nested under the API base path.
    mcp_path = _normalize_path(http_config.mcp_path, default="/mcp")
    health_path = _join_paths(
        base_path, _normalize_path(http_config.health_path, default="/health")
    )
    events_path = _join_paths(
        base_path, _normalize_path(http_config.events_path, default="/events")
    )

    resolved_host = (http_config.host or http_config.fallback_host or "").strip()
    if not resolved_host:
        resolved_host = "0.0.0.0"

    return HttpRuntimeSettings(
        transport=transport,
        host=resolved_host,
        port=_to_int(http_config.port, default=8000),
        mcp_path=mcp_path,
        health_path=health_path,
        events_path=events_path,
        stateless_http=_to_bool(http_config.stateless_http, default=False),
    )


def _resolve_path(
    policy: ScopePolicy | PosixScopePolicy, path: str, *, operation: str
) -> str:
    """Handle resolve path."""
    if isinstance(policy, ScopePolicy):
        resolved = policy.normalize(path)
        policy.require(resolved, operation=operation)
        return str(resolved)
    resolved_posix = policy.normalize(path)
    policy.require(str(resolved_posix), operation=operation)
    return str(resolved_posix)


def _validate_text(
    content_type: str, text: str, validation: ValidationConfig
) -> Dict[str, Any]:
    """Handle validate text."""
    result = validate_with_mode(content_type, text, validation)
    return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}


def _infer_content_type(path: str | Path) -> str:
    """Handle infer content type."""
    suffix = path_utils.suffix(str(path)).lower()
    mapping = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".htm": "html",
        ".md": "markdown",
        ".markdown": "markdown",
    }
    if suffix not in mapping:
        raise ValueError(f"Unsupported content type for file extension: {suffix}")
    return mapping[suffix]


def _normalize_optional_path(value: str | None) -> Path | None:
    """Handle normalize optional path."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or "${" in cleaned:
        return None
    return path_utils.as_path(path_utils.resolve_path(cleaned))


def _profile_ui_relative_path(path_value: str, scope_roots: list[str]) -> str:
    """Return a profile-scoped UI path when the target sits under a scope root."""
    candidate = str(path_value or "").strip()
    if not candidate:
        return ""

    candidate_path = Path(candidate)
    for root in scope_roots:
        root_text = str(root or "").strip()
        if not root_text:
            continue
        root_path = Path(root_text)
        if candidate_path.is_absolute() != root_path.is_absolute():
            continue
        try:
            relative = os.path.relpath(str(candidate_path), str(root_path))
        except ValueError:
            continue
        if relative in {".", ""}:
            return "."
        if relative == ".." or relative.startswith(f"..{os.sep}"):
            continue
        relative = relative.replace("\\", "/")
        return relative if relative.startswith("./") else f"./{relative}"

    return candidate


def build_tool_registry(
    profile: ProfileConfig,
    *,
    profile_name: str = "default",
    logger: LogLike | None = None,
    admin_identity_service: AdminIdentityService | None = None,
    jobs_runtime: FileMcpJobsRuntime | None = None,
) -> ToolRegistry:
    """Build tool registry."""
    backend = build_storage_backend(profile)
    # Alias to avoid accidental shadowing by tool parameters (e.g. convert_file has a `backend` arg).
    storage_backend = backend
    if backend.backend_name == "local":
        policy: ScopePolicy | PosixScopePolicy = ScopePolicy(
            roots=profile.scope.roots,
            allow_globs=profile.scope.allow_globs,
            deny_globs=profile.scope.deny_globs,
            allowed_exts=profile.scope.allowed_exts,
            read_only_exts=profile.scope.read_only_exts,
        )
    else:
        policy = PosixScopePolicy(
            roots=profile.scope.roots,
            allow_globs=profile.scope.allow_globs,
            deny_globs=profile.scope.deny_globs,
            allowed_exts=profile.scope.allowed_exts,
            read_only_exts=profile.scope.read_only_exts,
        )
    limits = profile.limits
    validation = profile.validation
    active_backend = storage_backend.backend_name
    audit_log_path = _normalize_optional_path(profile.audit.log_path)
    audit_logger = AuditLogger(audit_log_path) if audit_log_path else None
    snapshot_dir = _normalize_optional_path(profile.snapshots.dir)
    snapshots_enabled = bool(
        profile.snapshots.enabled and snapshot_dir and profile.snapshots.mode != "none"
    )
    snapshot_retention_days = profile.snapshots.retention_days

    def _request_user_id() -> str | None:
        """Extract caller identity from auth context when available."""
        token = get_access_token()
        if token is None:
            return None
        for attribute in ("subject", "sub", "identity", "principal", "user_id"):
            value = getattr(token, attribute, None)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        claims = getattr(token, "claims", None)
        if isinstance(claims, dict):
            for key in ("user_id", "subject", "sub", "identity", "principal"):
                value = claims.get(key)
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    return text
        client_id = getattr(token, "client_id", None)
        if client_id is not None:
            text = str(client_id).strip()
            if text:
                return text
        return None

    def _start_managed_job(job_type: str, payload: dict[str, Any]) -> str | None:
        """Submit and claim a managed job for this tool call."""
        if jobs_runtime is None:
            return None
        try:
            job_id = jobs_runtime.submit_job(
                job_type=job_type,
                payload=payload,
                session_id=get_request_session_id(),
                correlation_id=get_correlation_id(),
                user_id=_request_user_id(),
                request_ip=get_request_client_ip(),
            )
            jobs_runtime.mark_running(job_id)
            return job_id
        except Exception as exc:
            if logger is not None:
                logger.warning(
                    "managed_job_start_failed",
                    profile=profile_name,
                    job_type=job_type,
                    reason=str(exc),
                )
            return None

    def _finish_managed_job(payload: dict[str, Any], job_id: str | None) -> dict[str, Any]:
        """Attach job metadata and update lifecycle state."""
        if jobs_runtime is None or not job_id:
            return payload
        result = dict(payload)
        result["job_id"] = job_id
        try:
            if bool(result.get("ok")):
                jobs_runtime.mark_succeeded(job_id)
            else:
                warnings = result.get("warnings")
                if isinstance(warnings, list) and warnings:
                    error_message = str(warnings[0])
                else:
                    error_message = str(result.get("error_code") or "job_failed")
                error_code = str(result.get("error_code") or "").strip().lower()
                jobs_runtime.mark_failed(
                    job_id,
                    error=error_message,
                    retryable=error_code in {"backend_unavailable", "timeout"},
                )
        except Exception as exc:
            if logger is not None:
                logger.warning(
                    "managed_job_finish_failed",
                    profile=profile_name,
                    job_id=job_id,
                    reason=str(exc),
                )
        return result

    def _write_audit(
        *,
        tool_name: str,
        action: str,
        status: str,
        params: Dict[str, Any] | None = None,
        duration_ms: float | None = None,
        outcome: str | None = None,
        paths: Dict[str, str] | None = None,
        details: Dict[str, Any] | None = None,
    ) -> None:
        """Handle write audit."""
        if not audit_logger:
            return
        audit_logger.write(
            build_event(
                tool=tool_name,
                action=action,
                status=status,
                outcome=outcome or status,
                profile=profile_name,
                session_id=get_request_session_id(),
                client_ip=get_request_client_ip(),
                duration_ms=duration_ms,
                actor_id=_request_user_id(),
                actor_type="user",
                params=params or {},
                paths=paths or {},
                details={
                    "correlation_id": get_correlation_id(),
                    **(details or {}),
                },
            )
        )

    def _snapshot_if_enabled(resolved_path: str) -> Path | None:
        """Handle snapshot if enabled."""
        if not snapshots_enabled or not snapshot_dir:
            return None
        if backend.backend_name == "local":
            if not path_utils.exists(resolved_path):
                return None
            snapshot = create_snapshot(snapshot_dir, path_utils.as_path(resolved_path))
        else:
            stat = backend.stat(resolved_path)
            if stat is None:
                return None
            # Snapshots are byte-for-byte file backups.  A remote directory
            # has no byte representation, and attempting read_bytes here
            # prevents otherwise-supported directory deletion on WebDAV/FTP.
            if stat.is_dir:
                return None
            data = backend.read_bytes(resolved_path)
            snapshot = create_snapshot_bytes(snapshot_dir, resolved_path, data)
        prune_snapshots(
            snapshot_dir,
            snapshot_retention_days,
            profile.snapshots.retention_count,
            profile.snapshots.max_storage_mb,
        )
        return snapshot

    def _backend_health_snapshot() -> Dict[str, Any]:
        """Handle backend health snapshot."""
        states = ENDPOINT_HEALTH_MANAGER.get_profile_states(profile_name)
        return {
            "profile": profile_name,
            "active_backend": active_backend,
            "states": {name: state.__dict__.copy() for name, state in states.items()},
        }

    def _resolve_path_for_tool(
        *,
        tool_name: str,
        action: str,
        path: str,
        operation: str,
        path_key: str = "path",
    ) -> str:
        """Handle resolve path for tool."""
        try:
            return _resolve_path(policy, path, operation=operation)
        except Exception:
            _write_audit(
                tool_name=tool_name,
                action=action,
                status="error",
                paths={path_key: str(path)},
                details={"reason": "scope_denied_or_invalid_path"},
            )
            raise

    def _mutating_edit_file(
        *,
        tool_name: str,
        path: str,
        operation: str,
        content_type: str,
        transform,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Handle mutating edit file."""
        resolved = _resolve_path_for_tool(
            tool_name=tool_name,
            action=f"edit_{content_type}",
            path=path,
            operation=operation,
        )
        snapshot = _snapshot_if_enabled(resolved)
        before = backend.read_bytes(resolved).decode(encoding, errors="replace")
        try:
            updated = transform(before)
        except Exception as exc:
            _write_audit(
                tool_name=tool_name,
                action=f"edit_{content_type}",
                status="error",
                paths={"path": str(resolved)},
                details={"reason": "edit_transform_failed", "error": str(exc)},
            )
            raise
        validation_result = validate_with_mode(content_type, updated, validation)
        if not validation_result.valid:
            _write_audit(
                tool_name=tool_name,
                action=f"edit_{content_type}",
                status="error",
                paths={"path": str(resolved)},
                details={"validation_errors": validation_result.errors},
            )
            raise ValueError(f"{content_type.upper()} validation failed after edit")

        if dry_run:
            _write_audit(
                tool_name=tool_name,
                action=f"edit_{content_type}",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "dry_run": True,
                    "snapshot_path": str(snapshot) if snapshot else None,
                    "validation_warnings": validation_result.warnings,
                },
            )
            return {
                "ok": True,
                "path": str(resolved),
                "dry_run": True,
                "valid": validation_result.valid,
                "warnings": validation_result.warnings,
            }

        backend.write_bytes(resolved, updated.encode(encoding), overwrite=True)
        _write_audit(
            tool_name=tool_name,
            action=f"edit_{content_type}",
            status="ok",
            paths={"path": str(resolved)},
            details={
                "snapshot_path": str(snapshot) if snapshot else None,
                "validation_warnings": validation_result.warnings,
            },
        )
        return {
            "ok": True,
            "path": str(resolved),
            "dry_run": False,
            "valid": validation_result.valid,
            "warnings": validation_result.warnings,
        }

    def backend_status() -> Dict[str, Any]:
        """Execute backend status."""
        return _backend_health_snapshot()

    def _assert_admin_for_admin_tool() -> None:
        """Require an authenticated admin scope for admin management tools."""
        token = get_access_token()
        scopes = set(getattr(token, "scopes", []) or [])
        if not (
            "*" in scopes
            or "admin" in scopes
            or "admin:*" in scopes
            or "role:admin" in scopes
        ):
            raise PermissionError("Admin scope required")

    def read_file(
        path: str,
        encoding: str = "utf-8",
        start_line: int | None = None,
        end_line: int | None = None,
        start_byte: int | None = None,
        end_byte: int | None = None,
    ) -> str:
        """Read file."""
        resolved = _resolve_path(policy, path, operation="read")
        if (start_line is not None or end_line is not None) and (
            start_byte is not None or end_byte is not None
        ):
            raise ValueError("Cannot combine line and byte ranges")

        data = backend.read_bytes(resolved)
        if start_byte is not None or end_byte is not None:
            start = 0 if start_byte is None else max(start_byte, 0)
            end = len(data) if end_byte is None else max(end_byte, 0)
            if end < start:
                raise ValueError("end_byte must be >= start_byte")
            return data[start:end].decode(encoding, errors="replace")

        text = data.decode(encoding, errors="replace")
        if start_line is None and end_line is None:
            return text

        lines = text.splitlines(keepends=True)
        start_idx = 0 if start_line is None else max(start_line - 1, 0)
        end_idx = len(lines) if end_line is None else max(end_line, 0)
        if end_idx < start_idx:
            raise ValueError("end_line must be >= start_line")
        return "".join(lines[start_idx:end_idx])

    def write_file(
        path: str,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Write file."""
        resolved = _resolve_path_for_tool(
            tool_name="write_file",
            action="write",
            path=path,
            operation="write",
        )
        snapshot = _snapshot_if_enabled(resolved)
        try:
            if dry_run:
                _write_audit(
                    tool_name="write_file",
                    action="write",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={
                        "dry_run": True,
                        "snapshot_path": str(snapshot) if snapshot else None,
                    },
                )
                return {"ok": True, "path": str(resolved), "dry_run": True}
            backend.write_bytes(resolved, content.encode(encoding), overwrite=overwrite)
            _write_audit(
                tool_name="write_file",
                action="write",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "dry_run": False,
                    "snapshot_path": str(snapshot) if snapshot else None,
                },
            )
            return {"ok": True, "path": str(resolved), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="write_file",
                action="write",
                status="error",
                paths={"path": str(resolved)},
            )
            raise

    def delete_path(
        path: str, missing_ok: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Delete path."""
        resolved = _resolve_path_for_tool(
            tool_name="delete_file",
            action="delete",
            path=path,
            operation="delete",
        )
        snapshot = _snapshot_if_enabled(resolved)
        try:
            if dry_run:
                _write_audit(
                    tool_name="delete_file",
                    action="delete",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={
                        "dry_run": True,
                        "snapshot_path": str(snapshot) if snapshot else None,
                    },
                )
                return {"ok": True, "path": str(resolved), "dry_run": True}
            backend.delete_path(resolved, missing_ok=missing_ok)
            _write_audit(
                tool_name="delete_file",
                action="delete",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "dry_run": False,
                    "snapshot_path": str(snapshot) if snapshot else None,
                },
            )
            return {"ok": True, "path": str(resolved), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="delete_file",
                action="delete",
                status="error",
                paths={"path": str(resolved)},
            )
            raise

    def copy_path(
        src: str, dst: str, overwrite: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Copy path."""
        resolved_src = _resolve_path_for_tool(
            tool_name="copy_file",
            action="copy",
            path=src,
            operation="read",
            path_key="src",
        )
        resolved_dst = _resolve_path_for_tool(
            tool_name="copy_file",
            action="copy",
            path=dst,
            operation="copy",
            path_key="dst",
        )
        try:
            if dry_run:
                _write_audit(
                    tool_name="copy_file",
                    action="copy",
                    status="ok",
                    paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                    details={"dry_run": True},
                )
                return {
                    "ok": True,
                    "src": str(resolved_src),
                    "dst": str(resolved_dst),
                    "dry_run": True,
                }
            backend.copy_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name="copy_file",
                action="copy",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {
                "ok": True,
                "src": str(resolved_src),
                "dst": str(resolved_dst),
                "dry_run": False,
            }
        except Exception:
            _write_audit(
                tool_name="copy_file",
                action="copy",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def create_dir_path(
        path: str,
        parents: bool = True,
        exist_ok: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create dir path."""
        resolved = _resolve_path_for_tool(
            tool_name="create_dir",
            action="mkdir",
            path=path,
            operation="write",
        )
        try:
            if dry_run:
                _write_audit(
                    tool_name="create_dir",
                    action="mkdir",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={"dry_run": True, "parents": parents, "exist_ok": exist_ok},
                )
                return {"ok": True, "path": str(resolved), "dry_run": True}
            backend.create_dir(resolved, parents=parents, exist_ok=exist_ok)
            _write_audit(
                tool_name="create_dir",
                action="mkdir",
                status="ok",
                paths={"path": str(resolved)},
                details={"dry_run": False, "parents": parents, "exist_ok": exist_ok},
            )
            return {"ok": True, "path": str(resolved), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="create_dir",
                action="mkdir",
                status="error",
                paths={"path": str(resolved)},
            )
            raise

    def _parse_octal_mode(mode: int | str) -> int:
        """Handle parse octal mode."""
        if isinstance(mode, int):
            return mode
        if isinstance(mode, str):
            normalized = mode.strip().lower()
            if normalized.startswith("0o"):
                return int(normalized, 8)
            return int(normalized, 8)
        raise ValueError("mode must be an int or octal string")

    def chmod_fs_path(
        path: str, mode: int | str, recursive: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute chmod fs path."""
        resolved = _resolve_path_for_tool(
            tool_name="chmod_path",
            action="chmod",
            path=path,
            operation="write",
        )
        parsed_mode = _parse_octal_mode(mode)
        try:
            if dry_run:
                _write_audit(
                    tool_name="chmod_path",
                    action="chmod",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={
                        "dry_run": True,
                        "mode": oct(parsed_mode),
                        "recursive": recursive,
                    },
                )
                return {
                    "ok": True,
                    "path": str(resolved),
                    "mode": oct(parsed_mode),
                    "dry_run": True,
                }
            backend.chmod_path(resolved, parsed_mode, recursive=recursive)
            _write_audit(
                tool_name="chmod_path",
                action="chmod",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "dry_run": False,
                    "mode": oct(parsed_mode),
                    "recursive": recursive,
                },
            )
            return {
                "ok": True,
                "path": str(resolved),
                "mode": oct(parsed_mode),
                "dry_run": False,
            }
        except Exception:
            _write_audit(
                tool_name="chmod_path",
                action="chmod",
                status="error",
                paths={"path": str(resolved)},
            )
            raise

    def move_path_handler(
        src: str,
        dst: str,
        overwrite: bool = False,
        dry_run: bool = False,
        *,
        tool_name: str = "move_file",
    ) -> Dict[str, Any]:
        """Move path handler."""
        resolved_src = _resolve_path_for_tool(
            tool_name=tool_name,
            action="move",
            path=src,
            operation="move",
            path_key="src",
        )
        resolved_dst = _resolve_path_for_tool(
            tool_name=tool_name,
            action="move",
            path=dst,
            operation="move",
            path_key="dst",
        )
        try:
            if dry_run:
                _write_audit(
                    tool_name=tool_name,
                    action="move",
                    status="ok",
                    paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                    details={"dry_run": True},
                )
                return {
                    "ok": True,
                    "src": str(resolved_src),
                    "dst": str(resolved_dst),
                    "dry_run": True,
                }
            backend.move_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name=tool_name,
                action="move",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {
                "ok": True,
                "src": str(resolved_src),
                "dst": str(resolved_dst),
                "dry_run": False,
            }
        except Exception:
            _write_audit(
                tool_name=tool_name,
                action="move",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def rename_path_handler(
        src: str, dst: str, overwrite: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Rename path handler."""
        resolved_src = _resolve_path_for_tool(
            tool_name="rename_path",
            action="rename",
            path=src,
            operation="move",
            path_key="src",
        )
        resolved_dst = _resolve_path_for_tool(
            tool_name="rename_path",
            action="rename",
            path=dst,
            operation="move",
            path_key="dst",
        )
        try:
            if dry_run:
                _write_audit(
                    tool_name="rename_path",
                    action="rename",
                    status="ok",
                    paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                    details={"dry_run": True},
                )
                return {
                    "ok": True,
                    "src": str(resolved_src),
                    "dst": str(resolved_dst),
                    "dry_run": True,
                }
            backend.rename_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name="rename_path",
                action="rename",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {
                "ok": True,
                "src": str(resolved_src),
                "dst": str(resolved_dst),
                "dry_run": False,
            }
        except Exception:
            _write_audit(
                tool_name="rename_path",
                action="rename",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def list_path(path: str, recursive: bool = False) -> Dict[str, Any]:
        """List path."""
        resolved = _resolve_path(policy, path, operation="read")
        listed_entries = backend.list_dir(resolved, recursive=recursive)
        entries = [entry.path for entry in listed_entries]
        entry_details: list[dict[str, Any]] = []
        for entry in listed_entries:
            detail: dict[str, Any] = {
                "path": entry.path,
                "is_dir": bool(entry.is_dir),
                "size": getattr(entry, "size", None),
                "modified_at": getattr(entry, "modified_at", None),
                "created_at": getattr(entry, "created_at", None),
                "accessed_at": getattr(entry, "accessed_at", None),
                "owner": getattr(entry, "owner", None),
            }
            metadata = getattr(entry, "metadata", None)
            if isinstance(metadata, dict):
                detail["metadata"] = dict(metadata)
                for key, value in metadata.items():
                    if str(key).startswith("drive_"):
                        detail[str(key)] = value
            if backend.backend_name == "local":
                try:
                    stat_result = path_utils.file_stat(entry.path)
                    detail["size"] = int(stat_result.st_size)
                    detail["modified_at"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat_result.st_mtime)
                    )
                    detail["created_at"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat_result.st_ctime)
                    )
                    detail["accessed_at"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat_result.st_atime)
                    )
                    try:
                        detail["owner"] = pwd.getpwuid(stat_result.st_uid).pw_name
                    except KeyError:
                        detail["owner"] = str(stat_result.st_uid)
                except OSError:
                    pass
            entry_details.append(detail)
        return {"path": str(resolved), "entries": entries, "entry_details": entry_details}

    def search_path_names(
        query: str,
        path: str | None = None,
        glob: str | None = None,
        regex: bool = False,
        max_results: int | None = None,
        max_file_mb: int | None = None,
        max_depth: int | None = None,
        modified_after: str | None = None,
        modified_before: str | None = None,
        timeout_s: int | None = None,
    ) -> Dict[str, Any]:
        """Search path names."""
        effective_max_results = (
            max_results if max_results is not None else limits.search_max_results
        )
        effective_max_mb = (
            max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        )
        effective_timeout = (
            timeout_s if timeout_s is not None else limits.search_timeout_s
        )

        if backend.backend_name == "local":
            roots = [path_utils.as_path(path_utils.resolve_path(root)) for root in profile.scope.roots]
            with enforce_timeout(effective_timeout):
                matches = search_paths(
                    query,
                    roots=roots,
                    glob=glob,
                    regex=regex,
                    # Apply result caps after scope-policy filtering so denied
                    # matches do not consume the caller-visible quota.
                    max_results=None,
                    max_file_mb=effective_max_mb,
                    max_depth=max_depth,
                    modified_after=modified_after,
                    modified_before=modified_before,
                )
            filtered: list[str] = []
            for path_obj in matches:
                try:
                    assert isinstance(policy, ScopePolicy)
                    policy.require(path_utils.resolve_path(str(path_obj)), operation="read")
                    filtered.append(str(path_obj))
                    if (
                        effective_max_results is not None
                        and len(filtered) >= effective_max_results
                    ):
                        break
                except Exception:
                    continue
            return {"matches": filtered}

        import re

        pattern = re.compile(query) if regex else None
        remote_roots: list[str]
        if path is not None:
            requested_root = str(PosixScopePolicy.normalize(path))
            assert isinstance(policy, PosixScopePolicy)
            policy.require(requested_root, operation="read")
            remote_roots = [requested_root]
        else:
            remote_roots = [
                str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots
            ]

        def _depth_ok(root: str, candidate: str) -> bool:
            """Handle depth ok."""
            if max_depth is None:
                return True
            try:
                rel_parts = path_utils.relative_parts(candidate, root)
            except Exception:
                return False
            return len(rel_parts) <= max_depth

        remote_filtered: list[str] = []
        timed_out = False
        started = time.monotonic()
        for candidate in backend.iter_paths(remote_roots, max_depth=max_depth):
            if effective_timeout is not None and effective_timeout > 0:
                if (time.monotonic() - started) >= effective_timeout:
                    timed_out = True
                    break
            if glob and not path_utils.match_glob(candidate, glob):
                continue
            if not any(_depth_ok(root, candidate) for root in remote_roots):
                continue
            try:
                if effective_max_mb is not None:
                    stat = backend.stat(candidate)
                    if (
                        stat is not None
                        and stat.size is not None
                        and stat.size > effective_max_mb * 1024 * 1024
                    ):
                        continue
            except Exception:
                continue
            if regex:
                if pattern and pattern.search(candidate):
                    pass
                else:
                    continue
            else:
                if query not in candidate:
                    continue
            try:
                assert isinstance(policy, PosixScopePolicy)
                policy.require(candidate, operation="read")
            except Exception:
                continue
            remote_filtered.append(candidate)
            if (
                effective_max_results is not None
                and len(remote_filtered) >= effective_max_results
            ):
                break
        return {"matches": remote_filtered, "timed_out": timed_out}

    def search_text_content(
        query: str,
        glob: str | None = None,
        path: str | None = None,  # W28A-242: accept path as alias for glob (LLM compatibility)
        regex: bool = False,
        max_results: int | None = None,
        encoding: str = "utf-8",
        max_file_mb: int | None = None,
        max_depth: int | None = None,
        modified_after: str | None = None,
        modified_before: str | None = None,
        timeout_s: int | None = None,
    ) -> Dict[str, Any]:
        """Search text content."""
        # W28A-242: accept path as alias for glob
        if glob is None and path is not None:
            glob = f"{path}/**" if not any(c in path for c in ("*", "?")) else path
        effective_max_results = (
            max_results if max_results is not None else limits.search_max_results
        )
        effective_max_mb = (
            max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        )
        effective_timeout = (
            timeout_s if timeout_s is not None else limits.search_timeout_s
        )

        if backend.backend_name == "local":
            roots = [path_utils.as_path(path_utils.resolve_path(root)) for root in profile.scope.roots]
            with enforce_timeout(effective_timeout):
                matches = search_content(
                    query,
                    roots=roots,
                    glob=glob,
                    regex=regex,
                    encoding=encoding,
                    # Apply result caps after scope-policy filtering so denied
                    # matches do not consume the caller-visible quota.
                    max_results=None,
                    max_file_mb=effective_max_mb,
                    max_depth=max_depth,
                    modified_after=modified_after,
                    modified_before=modified_before,
                )
            filtered_matches = []
            for match in matches:
                try:
                    assert isinstance(policy, ScopePolicy)
                    policy.require(path_utils.resolve_path(str(match.path)), operation="read")
                    filtered_matches.append(match)
                    if (
                        effective_max_results is not None
                        and len(filtered_matches) >= effective_max_results
                    ):
                        break
                except Exception:
                    continue
            return {
                "matches": [
                    {
                        "path": str(match.path),
                        "line_no": match.line_no,
                        "line": match.line,
                    }
                    for match in filtered_matches
                ]
            }

        import re

        regex_pattern = re.compile(query) if regex else None
        remote_roots: list[str]
        if path is not None:
            requested_root = str(PosixScopePolicy.normalize(path))
            assert isinstance(policy, PosixScopePolicy)
            policy.require(requested_root, operation="read")
            remote_roots = [requested_root]
        else:
            remote_roots = [
                str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots
            ]
        results: list[dict[str, Any]] = []

        def _depth_ok(root: str, candidate: str) -> bool:
            """Handle depth ok."""
            if max_depth is None:
                return True
            try:
                rel_parts = path_utils.relative_parts(candidate, root)
            except Exception:
                return False
            return len(rel_parts) <= max_depth

        timed_out = False
        started = time.monotonic()
        for candidate in backend.iter_paths(remote_roots, max_depth=max_depth):
            if effective_timeout is not None and effective_timeout > 0:
                if (time.monotonic() - started) >= effective_timeout:
                    timed_out = True
                    break
            if glob and not path_utils.match_glob(candidate, glob):
                continue
            if not any(_depth_ok(root, candidate) for root in remote_roots):
                continue
            try:
                assert isinstance(policy, PosixScopePolicy)
                policy.require(candidate, operation="read")
            except Exception:
                continue
            try:
                if effective_max_mb is not None:
                    stat = backend.stat(candidate)
                    if (
                        stat is not None
                        and stat.size is not None
                        and stat.size > effective_max_mb * 1024 * 1024
                    ):
                        continue
            except Exception:
                continue
            try:
                text = backend.read_bytes(candidate).decode(encoding, errors="replace")
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                ok = (
                    regex_pattern.search(line) is not None
                    if regex and regex_pattern is not None
                    else (query in line)
                )
                if ok:
                    results.append(
                        {"path": candidate, "line_no": line_no, "line": line}
                    )
                    if (
                        effective_max_results is not None
                        and len(results) >= effective_max_results
                    ):
                        return {"matches": results, "timed_out": timed_out}
        return {"matches": results, "timed_out": timed_out}

    def json_set_file(
        path: str,
        json_path: str,
        value: Any,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute json set file."""
        return _mutating_edit_file(
            tool_name="json_set_file",
            path=path,
            operation="write",
            content_type="json",
            transform=lambda text: json_set(text, json_path, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def xml_set_file(
        path: str,
        xpath: str,
        value: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute xml set file."""
        return _mutating_edit_file(
            tool_name="xml_set_file",
            path=path,
            operation="edit",
            content_type="xml",
            transform=lambda text: xml_set(text, xpath, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def html_set_file(
        path: str,
        selector: str,
        value: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute html set file."""
        return _mutating_edit_file(
            tool_name="html_set_file",
            path=path,
            operation="edit",
            content_type="html",
            transform=lambda text: html_set(text, selector, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def markdown_set_section_file(
        path: str,
        heading: str | list[str],
        new_content: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute markdown set section file."""
        return _mutating_edit_file(
            tool_name="markdown_set_section_file",
            path=path,
            operation="edit",
            content_type="markdown",
            transform=lambda text: md_set_section(text, heading, new_content),
            encoding=encoding,
            dry_run=dry_run,
        )

    def markdown_set_frontmatter_file(
        path: str,
        updates: Dict[str, Any],
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute markdown set frontmatter file."""
        return _mutating_edit_file(
            tool_name="markdown_set_frontmatter_file",
            path=path,
            operation="edit",
            content_type="markdown",
            transform=lambda text: md_set_frontmatter(text, updates),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_set_file(
        path: str,
        yaml_path: str,
        value: Any,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute yaml set file."""
        return _mutating_edit_file(
            tool_name="yaml_set_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_set(text, yaml_path, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_delete_file(
        path: str,
        yaml_path: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute yaml delete file."""
        return _mutating_edit_file(
            tool_name="yaml_delete_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_delete(text, yaml_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def json_get_file(
        path: str, json_path: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Execute json get file."""
        resolved = _resolve_path(policy, path, operation="read")
        text = backend.read_bytes(resolved).decode(encoding, errors="replace")
        return {"ok": True, "path": str(resolved), "value": json_get(text, json_path)}

    def json_copy_file(
        path: str,
        from_path: str,
        to_path: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute json copy file."""
        return _mutating_edit_file(
            tool_name="json_copy_file",
            path=path,
            operation="write",
            content_type="json",
            transform=lambda text: json_copy(text, from_path, to_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def json_move_file(
        path: str,
        from_path: str,
        to_path: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute json move file."""
        return _mutating_edit_file(
            tool_name="json_move_file",
            path=path,
            operation="write",
            content_type="json",
            transform=lambda text: json_move(text, from_path, to_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def json_merge_file(
        path: str,
        value: Any,
        json_path: str = "/",
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute json merge file."""
        return _mutating_edit_file(
            tool_name="json_merge_file",
            path=path,
            operation="write",
            content_type="json",
            transform=lambda text: json_merge(text, json_path, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_get_file(
        path: str, yaml_path: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Execute yaml get file."""
        resolved = _resolve_path(policy, path, operation="read")
        text = backend.read_bytes(resolved).decode(encoding, errors="replace")
        return {"ok": True, "path": str(resolved), "value": yaml_get(text, yaml_path)}

    def yaml_copy_file(
        path: str,
        from_path: str,
        to_path: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute yaml copy file."""
        return _mutating_edit_file(
            tool_name="yaml_copy_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_copy(text, from_path, to_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_move_file(
        path: str,
        from_path: str,
        to_path: str,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute yaml move file."""
        return _mutating_edit_file(
            tool_name="yaml_move_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_move(text, from_path, to_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_merge_file(
        path: str,
        value: Any,
        yaml_path: str = "/",
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute yaml merge file."""
        return _mutating_edit_file(
            tool_name="yaml_merge_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_merge(text, yaml_path, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def convert_file_tool(
        path: str,
        target_format: str,
        output_path: str | None = None,
        max_input_mb: int | None = None,
        timeout_s: int | None = None,
        simulate_delay_s: float | None = None,
        backend: str | None = None,
    ) -> Dict[str, Any]:
        """Convert file tool."""
        resolved = _resolve_path(policy, path, operation="read")
        resolved_output = (
            _resolve_path(policy, output_path, operation="write")
            if output_path
            else None
        )
        job_id = _start_managed_job(
            "file.convert",
            {
                "path": str(resolved),
                "target_format": str(target_format),
                "output_path": str(resolved_output or ""),
                "backend": str(backend or ""),
            },
        )
        effective_max_mb = (
            max_input_mb
            if max_input_mb is not None
            else profile.conversion.max_input_mb
        )
        effective_timeout = (
            timeout_s if timeout_s is not None else limits.conversion_timeout_s
        )

        def _fail(
            message: str, *, backend: str | None = None, code: str = "conversion_error"
        ) -> Dict[str, Any]:
            """Handle fail."""
            return {
                "ok": False,
                "backend": backend,
                "used_fallback": False,
                "error_code": code,
                "warnings": [message],
            }

        def _done(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Attach managed job metadata and close lifecycle state."""
            return _finish_managed_job(payload, job_id)

        try:
            if backend == "builtin-text-copy":
                text_like_exts = {
                    ".txt",
                    ".md",
                    ".json",
                    ".yaml",
                    ".yml",
                    ".html",
                    ".xml",
                }
                if path_utils.suffix(
                    resolved
                ).lower() not in text_like_exts or target_format not in {
                    "txt",
                    "md",
                }:
                    return _done(
                        _fail(
                            "builtin-text-copy backend does not support input/target combination",
                            code="unsupported_format",
                        )
                    )
                content = storage_backend.read_bytes(resolved).decode(
                    "utf-8", errors="replace"
                )
                if resolved_output:
                    raise_if_operation_cancelled()
                    storage_backend.write_bytes(
                        resolved_output, content.encode("utf-8"), overwrite=True
                    )
                    return _done(
                        {
                            "ok": True,
                            "backend": "builtin-text-copy",
                            "used_fallback": False,
                            "warnings": [],
                            "output_path": str(resolved_output),
                        }
                    )
                return _done(
                    {
                        "ok": True,
                        "backend": "builtin-text-copy",
                        "used_fallback": False,
                        "warnings": [],
                        "content": content,
                    }
                )

            def _run_conversion() -> Any:
                if simulate_delay_s and simulate_delay_s > 0:
                    time.sleep(simulate_delay_s)
                    raise_if_operation_cancelled()
                # Conversion backends operate on local filesystem paths. For remote storage,
                # stage the input into a temporary file and optionally upload the output.
                if storage_backend.backend_name == "local":
                    input_path = path_utils.as_path(resolved)
                    if resolved_output:
                        import tempfile

                        with tempfile.TemporaryDirectory() as td:
                            staged_output = path_utils.as_path(
                                path_utils.join(td, f"output.{target_format}")
                            )
                            result = run_convert_file(
                                input_path,
                                target_format,
                                output_path=staged_output,
                                max_input_mb=effective_max_mb,
                                timeout_s=None,
                                preferred_backend=backend if backend else None,
                            )
                            raise_if_operation_cancelled()
                            if result.output_path:
                                storage_backend.write_bytes(
                                    resolved_output,
                                    path_utils.read_bytes(str(result.output_path)),
                                    overwrite=True,
                                )
                    else:
                        result = run_convert_file(
                            input_path,
                            target_format,
                            output_path=None,
                            max_input_mb=effective_max_mb,
                            timeout_s=None,
                            preferred_backend=backend if backend else None,
                        )
                        raise_if_operation_cancelled()
                    return result
                else:
                    import tempfile

                    ext = path_utils.suffix(resolved) or ""
                    with tempfile.TemporaryDirectory() as td:
                        in_path = path_utils.as_path(path_utils.join(td, f"input{ext}"))
                        path_utils.write_bytes(
                            str(in_path), storage_backend.read_bytes(resolved)
                        )
                        out_path = path_utils.as_path(
                            path_utils.join(td, f"output.{target_format}")
                        )
                        result = run_convert_file(
                            in_path,
                            target_format,
                            output_path=out_path,
                            max_input_mb=effective_max_mb,
                            timeout_s=None,
                            preferred_backend=backend if backend else None,
                        )
                        raise_if_operation_cancelled()
                        if resolved_output and result.output_path:
                            storage_backend.write_bytes(
                                resolved_output,
                                path_utils.read_bytes(str(result.output_path)),
                                overwrite=True,
                            )
                        return result

            # W28R-3013: enforce the conversion timeout regardless of the dispatch
            # thread. MCP tools are dispatched on anyio worker threads where the
            # signal-based enforce_timeout silently no-ops (proven identical on the
            # deployed 3.12 image and local 3.13). call_with_timeout raises
            # TimeoutError on overrun, caught below and mapped to code="timeout".
            result = call_with_timeout(_run_conversion, effective_timeout)
            payload: Dict[str, Any] = {
                "ok": True,
                "backend": result.backend or "auto",
                "used_fallback": False,
                "warnings": result.warnings,
            }
            if result.output_path:
                payload["output_path"] = (
                    str(resolved_output) if resolved_output else str(result.output_path)
                )
            if result.content is not None:
                payload["content"] = result.content
            return _done(payload)
        except BackendNotFoundError as exc:
            return _done(_fail(str(exc), backend=backend, code="unknown_backend"))
        except BackendUnavailableError as exc:
            return _done(_fail(str(exc), backend=backend, code="backend_unavailable"))
        except BackendCannotHandleError as exc:
            return _done(_fail(str(exc), backend=backend, code="unsupported_format"))
        except ConversionError as exc:
            # Deterministic built-in fallback for text-like sources when external backends are unavailable.
            text_like_exts = {".txt", ".md", ".json", ".yaml", ".yml", ".html", ".xml"}
            if path_utils.suffix(resolved).lower() in text_like_exts and target_format in {
                "txt",
                "md",
            }:
                if backend and backend != "builtin-text-copy":
                    return _done(_fail(str(exc), code="backend_unavailable"))
                content = storage_backend.read_bytes(resolved).decode(
                    "utf-8", errors="replace"
                )
                if resolved_output:
                    raise_if_operation_cancelled()
                    storage_backend.write_bytes(
                        resolved_output, content.encode("utf-8"), overwrite=True
                    )
                    return _done(
                        {
                            "ok": True,
                            "backend": "builtin-text-copy",
                            "used_fallback": True,
                            "warnings": ["fallback_text_copy"],
                            "output_path": str(resolved_output),
                        }
                    )
                return _done(
                    {
                        "ok": True,
                        "backend": "builtin-text-copy",
                        "used_fallback": True,
                        "warnings": ["fallback_text_copy"],
                        "content": content,
                    }
                )
            return _done(_fail(str(exc), code="backend_unavailable"))
        except TimeoutError as exc:
            return _done(_fail(str(exc), code="timeout"))
        except LimitError as exc:
            return _done(_fail(str(exc), code="limit_exceeded"))

    def meld_files_tool(path_a: str, path_b: str) -> Dict[str, Any]:
        """Execute meld files tool."""
        resolved_a = _resolve_path(policy, path_a, operation="read")
        resolved_b = _resolve_path(policy, path_b, operation="read")
        if backend.backend_name != "local":
            raise NotSupportedError("meld_files", backend=backend.backend_name)
        ok, message = launch_meld(resolved_a, resolved_b)
        return {
            "ok": ok,
            "path_a": str(resolved_a),
            "path_b": str(resolved_b),
            "warnings": [] if ok else [message],
            "message": message,
        }

    def b64_encode_file(path: str, urlsafe: bool = False) -> Dict[str, Any]:
        """Execute b64 encode file."""
        resolved = _resolve_path(policy, path, operation="read")
        data = backend.read_bytes(resolved)
        return {"ok": True, "data": b64_encode(data, urlsafe=urlsafe)}

    def b64_decode_to_file(
        path: str,
        data: str,
        urlsafe: bool = False,
        overwrite: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute b64 decode to file."""
        resolved = _resolve_path_for_tool(
            tool_name="b64_decode_to_file",
            action="write",
            path=path,
            operation="write",
        )
        job_id = _start_managed_job(
            "file.upload.b64_decode",
            {
                "path": str(resolved),
                "bytes_in": len(data),
                "dry_run": bool(dry_run),
            },
        )
        snapshot = _snapshot_if_enabled(resolved)
        decoded = b64_decode(data, urlsafe=urlsafe)
        try:
            if dry_run:
                _write_audit(
                    tool_name="b64_decode_to_file",
                    action="write",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={
                        "dry_run": True,
                        "bytes_written": len(decoded),
                        "snapshot_path": str(snapshot) if snapshot else None,
                    },
                )
                return _finish_managed_job(
                    {
                        "ok": True,
                        "path": str(resolved),
                        "dry_run": True,
                        "bytes_written": len(decoded),
                    },
                    job_id,
                )
            backend.write_bytes(resolved, decoded, overwrite=overwrite)
            _write_audit(
                tool_name="b64_decode_to_file",
                action="write",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "snapshot_path": str(snapshot) if snapshot else None,
                    "dry_run": False,
                },
            )
            return _finish_managed_job(
                {
                    "ok": True,
                    "path": str(resolved),
                    "bytes_written": len(decoded),
                    "dry_run": False,
                },
                job_id,
            )
        except Exception as exc:
            _write_audit(
                tool_name="b64_decode_to_file",
                action="write",
                status="error",
                paths={"path": str(resolved)},
            )
            if jobs_runtime is not None and job_id:
                jobs_runtime.mark_failed(job_id, error=str(exc))
            raise

    def validate_file(
        path: str, content_type: str | None = None, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Validate file."""
        resolved = _resolve_path(policy, path, operation="read")
        resolved_type = content_type or _infer_content_type(resolved)
        text = backend.read_bytes(resolved).decode(encoding, errors="replace")
        result = validate_with_mode(resolved_type, text, validation)
        return {
            "ok": True,
            "path": str(resolved),
            "content_type": resolved_type,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    def diff_files_tool(
        path_a: str, path_b: str, encoding: str = "utf-8", context: int = 3
    ) -> Dict[str, Any]:
        """Execute diff files tool."""
        resolved_a = _resolve_path(policy, path_a, operation="read")
        resolved_b = _resolve_path(policy, path_b, operation="read")
        a_text = backend.read_bytes(resolved_a).decode(encoding, errors="replace")
        b_text = backend.read_bytes(resolved_b).decode(encoding, errors="replace")
        return {
            "ok": True,
            "diff": diff_text(
                a_text,
                b_text,
                context=context,
                fromfile=str(resolved_a),
                tofile=str(resolved_b),
            ),
            "path_a": str(resolved_a),
            "path_b": str(resolved_b),
        }

    def sed_edit_file(
        path: str,
        op: str | None = None,
        pattern: str | None = None,
        repl: str | None = None,
        count: int = 0,
        line_no: int | None = None,
        content: str | None = None,
        start: int | None = None,
        end: int | None = None,
        replacement: list[str] | None = None,
        operations: list[dict[str, Any]] | None = None,
        dry_run: bool = False,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Execute sed edit file."""
        resolved = _resolve_path_for_tool(
            tool_name="sed_edit_file",
            action="edit_text",
            path=path,
            operation="edit",
        )
        snapshot = _snapshot_if_enabled(resolved)
        before = backend.read_bytes(resolved).decode(encoding, errors="replace")

        def _apply_single(current: str, op_args: Dict[str, Any]) -> str:
            """Handle apply single."""
            single_op = op_args.get("op")
            # Accept "replace" as alias for "replace_regex" (W28A-242)
            if single_op == "replace":
                single_op = "replace_regex"
            if single_op == "replace_regex":
                single_pattern = op_args.get("pattern")
                single_repl = op_args.get("repl")
                single_count = int(op_args.get("count", 0))
                if single_pattern is None or single_repl is None:
                    raise ValueError("pattern and repl are required for replace_regex")
                return replace_regex(
                    current, single_pattern, single_repl, count=single_count
                ).text
            if single_op == "insert_before_line":
                single_line_no = op_args.get("line_no")
                single_content = op_args.get("content")
                if single_line_no is None or single_content is None:
                    raise ValueError(
                        "line_no and content are required for insert_before_line"
                    )
                return insert_before_line(
                    current, int(single_line_no), str(single_content)
                ).text
            if single_op == "insert_after_line":
                single_line_no = op_args.get("line_no")
                single_content = op_args.get("content")
                if single_line_no is None or single_content is None:
                    raise ValueError(
                        "line_no and content are required for insert_after_line"
                    )
                return insert_after_line(
                    current, int(single_line_no), str(single_content)
                ).text
            if single_op == "delete_matching_lines":
                single_pattern = op_args.get("pattern")
                if single_pattern is None:
                    raise ValueError("pattern is required for delete_matching_lines")
                return delete_matching_lines(current, str(single_pattern)).text
            if single_op == "replace_line_range":
                single_start = op_args.get("start")
                single_end = op_args.get("end")
                if single_start is None or single_end is None:
                    raise ValueError(
                        "start and end are required for replace_line_range"
                    )
                return replace_line_range(
                    current,
                    int(single_start),
                    int(single_end),
                    op_args.get("replacement") or [],
                ).text
            raise ValueError(f"Unsupported sed op: {single_op}")

        operation_label = op
        if operations is not None:
            if op is not None:
                raise ValueError("Provide either op or operations, not both")
            if not operations:
                raise ValueError("operations must be a non-empty list")
            updated = before
            for op_args in operations:
                updated = _apply_single(updated, op_args)
            operation_label = "transaction"
        else:
            if op is None:
                raise ValueError("op is required when operations is not provided")
            updated = _apply_single(
                before,
                {
                    "op": op,
                    "pattern": pattern,
                    "repl": repl,
                    "count": count,
                    "line_no": line_no,
                    "content": content,
                    "start": start,
                    "end": end,
                    "replacement": replacement,
                },
            )

        suffix = path_utils.suffix(resolved).lower()
        content_type = (
            "markdown"
            if suffix == ".md"
            else "html"
            if suffix == ".html"
            else "json"
            if suffix == ".json"
            else ""
        )
        if content_type:
            validation_result = validate_with_mode(content_type, updated, validation)
            if not validation_result.valid:
                _write_audit(
                    tool_name="sed_edit_file",
                    action="edit_text",
                    status="error",
                    paths={"path": str(resolved)},
                    details={"validation_errors": validation_result.errors},
                )
                raise ValueError("validation failed after sed edit")
            warnings = validation_result.warnings
        else:
            warnings = []

        try:
            if dry_run:
                _write_audit(
                    tool_name="sed_edit_file",
                    action="edit_text",
                    status="ok",
                    paths={"path": str(resolved)},
                    details={
                        "dry_run": True,
                        "snapshot_path": str(snapshot) if snapshot else None,
                        "op": operation_label,
                    },
                )
                return {
                    "ok": True,
                    "path": str(resolved),
                    "warnings": warnings,
                    "dry_run": True,
                }
            backend.write_bytes(resolved, updated.encode(encoding), overwrite=True)
            _write_audit(
                tool_name="sed_edit_file",
                action="edit_text",
                status="ok",
                paths={"path": str(resolved)},
                details={
                    "snapshot_path": str(snapshot) if snapshot else None,
                    "op": operation_label,
                    "dry_run": False,
                },
            )
            return {
                "ok": True,
                "path": str(resolved),
                "warnings": warnings,
                "dry_run": False,
            }
        except Exception:
            _write_audit(
                tool_name="sed_edit_file",
                action="edit_text",
                status="error",
                paths={"path": str(resolved)},
                details={"op": operation_label},
            )
            raise

    def admin_list_users() -> Dict[str, Any]:
        """List admin users."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "users": admin_identity_service.list_users()}

    def admin_create_user(
        username: str,
        display_name: str = "",
        is_active: bool = True,
        groups: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Create admin user."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        user = admin_identity_service.create_user(
            username=username,
            display_name=display_name,
            is_active=is_active,
            groups=groups or [],
        )
        _publish_config_event(
            resource="user",
            action="create",
            identifier=str(user.get("user_id") or user.get("id") or username),
            after=dict(user),
        )
        return {"ok": True, "user": user}

    def admin_update_user(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update admin user."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        user = admin_identity_service.update_user(user_id, data=data)
        _publish_config_event(
            resource="user",
            action="update",
            identifier=str(user_id),
            after=dict(user),
        )
        return {"ok": True, "user": user}

    def admin_delete_user(user_id: str) -> Dict[str, Any]:
        """Delete admin user."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        result = admin_identity_service.delete_user(user_id)
        _publish_config_event(
            resource="user",
            action="delete",
            identifier=str(user_id),
            before=dict(result) if isinstance(result, dict) else None,
        )
        return {"ok": True, "result": result}

    def admin_list_groups() -> Dict[str, Any]:
        """List admin groups."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "groups": admin_identity_service.list_groups()}

    def admin_create_group(
        name: str,
        description: str = "",
        roles: list[str] | None = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """Create admin group."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        group = admin_identity_service.create_group(
            name=name,
            description=description,
            roles=roles or [],
            is_active=is_active,
        )
        _publish_config_event(
            resource="group",
            action="create",
            identifier=str(group.get("group_id") or group.get("id") or name),
            after=dict(group),
        )
        return {"ok": True, "group": group}

    def admin_update_group(group_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update admin group."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        group = admin_identity_service.update_group(group_id, data=data)
        _publish_config_event(
            resource="group",
            action="update",
            identifier=str(group_id),
            after=dict(group),
        )
        return {"ok": True, "group": group}

    def admin_delete_group(group_id: str) -> Dict[str, Any]:
        """Delete admin group."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        result = admin_identity_service.delete_group(group_id)
        _publish_config_event(
            resource="group",
            action="delete",
            identifier=str(group_id),
            before=dict(result) if isinstance(result, dict) else None,
        )
        return {"ok": True, "result": result}

    def admin_list_api_keys(include_inactive: bool = False) -> Dict[str, Any]:
        """List admin API keys."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {
            "ok": True,
            "api_keys": admin_identity_service.list_api_keys(
                include_inactive=include_inactive
            ),
        }

    def admin_create_api_key(
        user_id: str,
        label: str,
        scopes: list[str] | None = None,
        profile_name: str = "",
    ) -> Dict[str, Any]:
        """Create admin API key."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        api_key = admin_identity_service.create_api_key(
            user_id=user_id,
            label=label,
            scopes=scopes or [],
            profile_name=profile_name,
        )
        # Redact raw token material from the event before fan-out.
        api_key_event_payload = {
            k: v for k, v in dict(api_key).items() if k not in {"api_key", "secret", "token"}
        }
        _publish_config_event(
            resource="api_key",
            action="create",
            identifier=str(api_key.get("api_key_id") or api_key.get("id") or label),
            after=api_key_event_payload,
        )
        return {"ok": True, "api_key": api_key}

    def admin_revoke_api_key(api_key_id: str) -> Dict[str, Any]:
        """Revoke admin API key."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        api_key = admin_identity_service.revoke_api_key(api_key_id)
        api_key_event_payload = (
            {k: v for k, v in dict(api_key).items() if k not in {"api_key", "secret", "token"}}
            if isinstance(api_key, dict)
            else None
        )
        _publish_config_event(
            resource="api_key",
            action="revoke",
            identifier=str(api_key_id),
            before=api_key_event_payload,
        )
        return {"ok": True, "api_key": api_key}

    from file_tools.tools.schemas import (
        ReadFileInput, WriteFileInput, CreateDirInput, ListDirInput,
        ConvertFileInput, ValidateFileInput, SearchContentInput,
        SedEditFileInput, ReplaceRegexInput, SearchPathsInput,
    )

    tools = ToolRegistry()
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="read_file", description="Read a text file. Parameters: path (required, file path relative to workspace root), encoding (optional, default utf-8)"),
            schema_def=ToolSchema(input_model=ReadFileInput),
            handler=read_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="write_file",
                description="Write text to a file. Parameters: path (required, file path), content (required, text to write), overwrite (optional, default true), dry_run (optional, default false)",
                mutating=True,
                supports_dry_run=True,
            ),
            schema_def=ToolSchema(input_model=WriteFileInput),
            handler=write_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="delete_file",
                description="Delete a file",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=delete_path,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="copy_file",
                description="Copy a file",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=copy_path,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="create_dir",
                description="Create a directory. Parameters: path (required, directory path), parents (optional, default true), dry_run (optional)",
                mutating=True,
                supports_dry_run=True,
            ),
            schema_def=ToolSchema(input_model=CreateDirInput),
            handler=create_dir_path,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="chmod_path",
                description="Change file or directory mode",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=chmod_fs_path,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="move_file",
                description="Move a file or directory",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=move_path_handler,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="move_path",
                description="Move a file or directory",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=lambda src, dst, overwrite=False, dry_run=False: move_path_handler(
                src,
                dst,
                overwrite=overwrite,
                dry_run=dry_run,
                tool_name="move_path",
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="rename_path",
                description="Rename a file or directory",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=rename_path_handler,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="list_dir", description="List directory entries. Parameters: path (optional, default '.'), recursive (optional, default false)"),
            schema_def=ToolSchema(input_model=ListDirInput),
            handler=list_path,
        )
    )
    # W28C-1702 (FM7): advertise `query` (handler is search_path_names(query=...))
    # so callers send the right field and normalize_and_filter_tool_args keeps it
    # (an empty schema + the `name`->`path` alias caused `TypeError: missing query`);
    # and register search_path_names as a documented alias so direct calls resolve
    # (was `Unknown tool: search_path_names`). index-retriever W28A-824 uses `query`.
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="search_paths",
                description="Search file paths by name. Parameters: query (required, filename pattern), path (optional, directory subtree), glob (optional), regex (optional), max_results (optional)",
            ),
            schema_def=ToolSchema(input_model=SearchPathsInput),
            handler=search_path_names,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="search_path_names",
                description="Alias of search_paths. Search file paths by name. Parameters: query (required), path (optional, directory subtree), glob, regex, max_results.",
            ),
            schema_def=ToolSchema(input_model=SearchPathsInput),
            handler=search_path_names,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="search_content", description="Search file contents. Parameters: query (required, search text), path (optional, directory to search), recursive (optional, default true)"),
            schema_def=ToolSchema(input_model=SearchContentInput),
            handler=search_text_content,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="diff_text", description="Generate unified diff for text"
            ),
            handler=lambda before, after, context=3: diff_text(
                before, after, context=context
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="b64_encode", description="Encode text as base64"),
            handler=lambda text, encoding="utf-8", urlsafe=False: b64_encode(
                text.encode(encoding), urlsafe=urlsafe
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="b64_decode", description="Decode base64 to text"),
            handler=lambda data, encoding="utf-8", urlsafe=False: b64_decode(
                data, urlsafe=urlsafe
            ).decode(encoding),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="b64_encode_file", description="Encode file contents as base64"
            ),
            handler=b64_encode_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="b64_decode_to_file",
                description="Decode base64 to file",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=b64_decode_to_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="validate_text",
                description="Validate text content by type",
                requires_validation=True,
            ),
            handler=lambda content_type, text: _validate_text(
                content_type, text, validation
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="validate_file",
                description="Validate file content by detected or explicit type. Parameters: path (required, file path), content_type (optional, e.g. yaml/json)",
                requires_validation=True,
            ),
            schema_def=ToolSchema(input_model=ValidateFileInput),
            handler=validate_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="json_get", description="Get JSON value by path"),
            handler=lambda text, path: json_get(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_set", description="Set JSON value by path", mutating=True
            ),
            handler=lambda text, path, value: json_set(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_delete",
                description="Delete JSON value by path",
                mutating=True,
            ),
            handler=lambda text, path: json_delete(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_copy", description="Copy JSON value by path", mutating=True
            ),
            handler=lambda text, from_path, to_path: json_copy(
                text, from_path, to_path
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_move", description="Move JSON value by path", mutating=True
            ),
            handler=lambda text, from_path, to_path: json_move(
                text, from_path, to_path
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_merge", description="Merge JSON value by path", mutating=True
            ),
            handler=lambda text, path, value: json_merge(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_get", description="Get YAML value by path"),
            handler=lambda text, path: yaml_get(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_set", description="Set YAML value by path", mutating=True
            ),
            handler=lambda text, path, value: yaml_set(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_delete",
                description="Delete YAML value by path",
                mutating=True,
            ),
            handler=lambda text, path: yaml_delete(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_copy", description="Copy YAML value by path", mutating=True
            ),
            handler=lambda text, from_path, to_path: yaml_copy(
                text, from_path, to_path
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_move", description="Move YAML value by path", mutating=True
            ),
            handler=lambda text, from_path, to_path: yaml_move(
                text, from_path, to_path
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_merge", description="Merge YAML value by path", mutating=True
            ),
            handler=lambda text, path, value: yaml_merge(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="markdown_get_section", description="Extract markdown section"
            ),
            handler=lambda text, heading: md_get_section(text, heading),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="markdown_set_section",
                description="Replace markdown section",
                mutating=True,
            ),
            handler=lambda text, heading, new_content: md_set_section(
                text, heading, new_content
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="replace_regex",
                description="Apply regex replacement",
                mutating=True,
            ),
            handler=lambda text, pattern, repl, count=0: (
                replace_regex(text, pattern, repl, count=count).text
            ),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="diff_files", description="Generate unified diff for files"
            ),
            handler=diff_files_tool,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="meld_files",
                description="Launch meld for file comparison (optional integration)",
            ),
            handler=meld_files_tool,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_set_file",
                description="Set JSON value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=json_set_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_copy_file",
                description="Copy JSON value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=json_copy_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_move_file",
                description="Move JSON value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=json_move_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_merge_file",
                description="Merge JSON value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=json_merge_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="xml_set_file",
                description="Set XML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=xml_set_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_set_file",
                description="Set YAML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=yaml_set_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_delete_file",
                description="Delete YAML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=yaml_delete_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_copy_file",
                description="Copy YAML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=yaml_copy_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_move_file",
                description="Move YAML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=yaml_move_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="html_set_file",
                description="Set HTML value in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=html_set_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="markdown_set_section_file",
                description="Set markdown section in file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=markdown_set_section_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="markdown_set_frontmatter_file",
                description="Update markdown YAML frontmatter with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=markdown_set_frontmatter_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="convert_file",
                description="Convert file format. Parameters: path (required, source file), target_format (required, e.g. html/txt/pdf), output_path (optional)",
                mutating=False,
            ),
            schema_def=ToolSchema(input_model=ConvertFileInput),
            handler=convert_file_tool,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="json_get_file", description="Get JSON value from file by path"
            ),
            handler=json_get_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_get_file", description="Get YAML value from file by path"
            ),
            handler=yaml_get_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="yaml_merge_file",
                description="Merge YAML mapping into file with validation/audit/snapshot",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            handler=yaml_merge_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="sed_edit_file",
                description="Apply sed-like file edits. Parameters: path (required, file path), op (optional, replace/delete/insert), pattern (optional, regex), repl (optional, replacement text), dry_run (optional)",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
            schema_def=ToolSchema(input_model=SedEditFileInput),
            handler=sed_edit_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="backend_status",
                description="Return endpoint health states for configured storage backends",
            ),
            handler=backend_status,
        )
    )
    if admin_identity_service is not None:
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_list_users",
                    description="List managed admin users",
                ),
                handler=admin_list_users,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_create_user",
                    description="Create managed admin user",
                    mutating=True,
                ),
                handler=admin_create_user,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_update_user",
                    description="Update managed admin user",
                    mutating=True,
                ),
                handler=admin_update_user,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_delete_user",
                    description="Delete managed admin user",
                    mutating=True,
                ),
                handler=admin_delete_user,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_list_groups",
                    description="List managed admin groups",
                ),
                handler=admin_list_groups,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_create_group",
                    description="Create managed admin group",
                    mutating=True,
                ),
                handler=admin_create_group,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_update_group",
                    description="Update managed admin group",
                    mutating=True,
                ),
                handler=admin_update_group,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_delete_group",
                    description="Delete managed admin group",
                    mutating=True,
                ),
                handler=admin_delete_group,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_list_api_keys",
                    description="List managed admin API keys",
                ),
                handler=admin_list_api_keys,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_create_api_key",
                    description="Create managed admin API key",
                    mutating=True,
                ),
                handler=admin_create_api_key,
            )
        )
        tools.register(
            ToolDefinition(
                meta=ToolMeta(
                    name="admin_revoke_api_key",
                    description="Revoke managed admin API key",
                    mutating=True,
                ),
                handler=admin_revoke_api_key,
            )
        )
    # ── W28E-1870-B server-mediated capture (CSTREAM-FILE-002, PS-102 §6) ──
    # Wrap every mutation tool handler so a change made THROUGH file-mcp is
    # captured natively (no polling/scan, no busy-wait) and fanned to matching
    # live watches, regardless of the transport (stdio / HTTP MCP / A2A / REST)
    # — they all resolve through this registry. Capture is best-effort and MUST
    # NOT change the tool result or crash the mutating request path.
    from file_tools.change_stream import TOOL_ACTION_MAP as _WATCH_TOOL_ACTIONS

    def _wrap_capture(tool_name: str, action: str, inner: Callable[..., Any]) -> Callable[..., Any]:
        import functools
        import inspect

        try:
            _inner_sig = inspect.signature(inner)
        except (TypeError, ValueError):  # pragma: no cover - builtins etc.
            _inner_sig = None

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            # forward args verbatim so positional AND keyword callers are unchanged
            result = inner(*args, **kwargs)
            try:
                # bind to the inner signature to resolve path/src regardless of how
                # the caller passed them (positional or keyword).
                bound: dict[str, Any] = dict(kwargs)
                if _inner_sig is not None and args:
                    ba = _inner_sig.bind_partial(*args, **kwargs)
                    bound = dict(ba.arguments)
                path = str(
                    bound.get("path")
                    or bound.get("dst")
                    or bound.get("target")
                    or bound.get("dest")
                    or ""
                )
                if path:
                    old_path = str(bound.get("src") or bound.get("source") or "")
                    get_shared_watch_service().observe_change(
                        tenant_id=str(profile_name or "default"),
                        profile_id=str(profile_name or "default"),
                        path=path,
                        action=action,
                        backend=str(active_backend or ""),
                        old_path=old_path if action in {"renamed", "moved"} else "",
                        capture="server_mediated",
                    )
            except Exception:  # pragma: no cover - capture never breaks the mutation
                pass
            return result

        # preserve the wrapped signature so normalize_and_filter_tool_args + the
        # tools/list schema builder + positional callers all see the real handler.
        try:
            functools.update_wrapper(_wrapped, inner)
        except Exception:  # pragma: no cover
            _wrapped.__name__ = getattr(inner, "__name__", tool_name)
        return _wrapped

    for _mut_name, _mut_action in _WATCH_TOOL_ACTIONS.items():
        try:
            _existing = tools.get(_mut_name)
        except Exception:
            continue
        _wrapped_def = _existing.model_copy(
            update={"handler": _wrap_capture(_mut_name, _mut_action, _existing.handler)}
        )
        # Replace in place — ToolRegistry.register refuses duplicate names.
        tools._tools[_mut_name] = _wrapped_def  # noqa: SLF001

    # ── W28E-1870-B storage change-watch MCP tools (PS-102 §5.3 / CSTREAM-FILE) ──
    # file_watch_{create,list,status,get_batch,ack,recover,pause,resume,delete,
    # test_event} + file_watch_backend_support. Dispatched onto the process-shared
    # WatchService (durable journal + broadcaster owned by the ASGI middleware).
    # MCP transport requires the `initialize` handshake before dispatch (the
    # api-kit MCP layer enforces this); these tools re-implement no journal/cursor.
    _watch_default_tenant = profile_name or "default"

    def _watch_tenant(arguments: dict[str, Any]) -> str:
        return str(arguments.get("tenant_id") or arguments.get("profile") or _watch_default_tenant)

    def file_watch_create(**arguments: Any) -> dict[str, Any]:
        ws = get_shared_watch_service()
        return ws.create_watch(
            profile_id=str(arguments.get("profile") or arguments.get("profile_id") or profile_name),
            tenant_id=_watch_tenant(arguments),
            actor=str(arguments.get("actor") or "mcp"),
            backend=str(arguments.get("backend") or active_backend),
            criteria=arguments.get("criteria") if isinstance(arguments.get("criteria"), dict) else None,
            max_batch=int(arguments.get("max_batch", 100)),
            max_inflight=int(arguments.get("max_inflight", 4)),
            journal_max=int(arguments.get("journal_max", 1000)),
            journal_ttl_seconds=(
                float(arguments["journal_ttl_seconds"])
                if arguments.get("journal_ttl_seconds") not in (None, "")
                else None
            ),
        )

    def file_watch_list(**arguments: Any) -> dict[str, Any]:
        return {"watches": get_shared_watch_service().list_watches(tenant_id=_watch_tenant(arguments))}

    def file_watch_status(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().get_status(
            str(arguments["watch_id"]), tenant_id=_watch_tenant(arguments)
        )

    def file_watch_get_batch(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().get_batch(
            str(arguments["watch_id"]),
            tenant_id=_watch_tenant(arguments),
            since_cursor=arguments.get("since_cursor") or None,
            max_batch=int(arguments["max_batch"]) if arguments.get("max_batch") else None,
        )

    def file_watch_ack(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().ack(
            str(arguments["watch_id"]),
            tenant_id=_watch_tenant(arguments),
            ack_cursor=str(arguments["ack_cursor"]),
        )

    def file_watch_recover(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().recover(
            str(arguments["watch_id"]),
            tenant_id=_watch_tenant(arguments),
            since_cursor=arguments.get("since_cursor") or None,
        )

    def file_watch_pause(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().pause(
            str(arguments["watch_id"]), tenant_id=_watch_tenant(arguments)
        )

    def file_watch_resume(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().resume(
            str(arguments["watch_id"]), tenant_id=_watch_tenant(arguments)
        )

    def file_watch_delete(**arguments: Any) -> dict[str, Any]:
        return get_shared_watch_service().delete(
            str(arguments["watch_id"]), tenant_id=_watch_tenant(arguments)
        )

    def file_watch_test_event(**arguments: Any) -> dict[str, Any]:
        extra = {
            k: v
            for k, v in arguments.items()
            if k not in {"watch_id", "tenant_id", "profile", "profile_id", "actor", "action", "object_ref"}
        }
        return get_shared_watch_service().test_event(
            str(arguments["watch_id"]),
            tenant_id=_watch_tenant(arguments),
            action=str(arguments.get("action", "created")),
            object_ref=str(arguments.get("object_ref", "test")),
            **extra,
        )

    def file_watch_backend_support(**arguments: Any) -> dict[str, Any]:
        backend = arguments.get("backend")
        return {"backend_support": get_shared_watch_service().backend_support(backend)}

    for _wt_name, _wt_handler, _wt_desc, _wt_mut in (
        ("file_watch_create", file_watch_create, "Create a storage change-watch (glob/regex criteria)", True),
        ("file_watch_list", file_watch_list, "List storage change-watches for the tenant/profile", False),
        ("file_watch_status", file_watch_status, "Get a storage change-watch status", False),
        ("file_watch_get_batch", file_watch_get_batch, "Get a bounded batch of change events (pull-batch)", False),
        ("file_watch_ack", file_watch_ack, "Acknowledge a change-watch cursor", False),
        ("file_watch_recover", file_watch_recover, "Recover/re-enquire a change-watch from a cursor", False),
        ("file_watch_pause", file_watch_pause, "Pause a storage change-watch", True),
        ("file_watch_resume", file_watch_resume, "Resume a storage change-watch", True),
        ("file_watch_delete", file_watch_delete, "Delete a storage change-watch and its journal", True),
        ("file_watch_test_event", file_watch_test_event, "Inject a deterministic synthetic change event", True),
        ("file_watch_backend_support", file_watch_backend_support, "Report change-watch backend support matrix", False),
    ):
        tools.register(
            ToolDefinition(
                meta=ToolMeta(name=_wt_name, description=_wt_desc, mutating=_wt_mut),
                handler=_wt_handler,
            )
        )

    setattr(tools, "profile_config", profile)
    setattr(tools, "profile_name", profile_name)
    setattr(tools, "storage_backend_name", active_backend)
    setattr(tools, "endpoint_health_manager", ENDPOINT_HEALTH_MANAGER)
    setattr(tools, "logger", logger)
    setattr(tools, "audit_writer", _write_audit)
    setattr(tools, "jobs_runtime", jobs_runtime)
    return tools


def _truncate_value(value: Any) -> Any:
    """Handle truncate value."""
    if isinstance(value, str):
        return value if len(value) <= 500 else f"{value[:500]}...[truncated]"
    if isinstance(value, dict):
        return {str(key): _truncate_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_truncate_value(item) for item in value]
    return value


def create_profile_tool_handler(
    registry_provider: Callable[..., ToolRegistry],
    tool_name: str,
    *,
    default_profile_name: str,
    logger: LogLike | None = None,
) -> Callable[..., Any]:
    """Build tool callable with logging, endpoint health, and audit writer hooks."""

    def _extract_paths_from_params(params: Dict[str, Any]) -> Dict[str, str]:
        """Handle extract paths from params."""
        path_keys = ("path", "src", "dst", "path_a", "path_b")
        extracted: Dict[str, str] = {}
        for key in path_keys:
            value = params.get(key)
            if isinstance(value, str):
                extracted[key] = value
        return extracted

    def wrapped_handler(*args, **kwargs):
        """Execute wrapped handler."""
        started = time.perf_counter()
        # W28C-1702 (FM3): an explicit per-call ``profile`` argument selects the
        # storage profile to dispatch against (explicit arg > request header /
        # context-var > default). Pop it so it is NOT forwarded to the raw tool
        # handler (whose signature does not accept it) and is not logged as a
        # tool argument.
        explicit_profile = kwargs.pop("profile", None)
        explicit_profile = (
            str(explicit_profile).strip() if explicit_profile is not None else ""
        )
        params = _truncate_value(kwargs)
        paths = _extract_paths_from_params(kwargs)
        profile_name = (
            explicit_profile
            or get_request_profile_name(default_profile_name)
            or default_profile_name
        )
        if explicit_profile:
            # Make the selected profile authoritative for scope checks, audit,
            # and downstream get_request_profile_name() reads in this request.
            set_request_profile_name(explicit_profile)
        registry = registry_provider(profile_name)
        current_def = registry.get(tool_name)
        raw_tool_handler = current_def.handler
        audit_writer = getattr(registry, "audit_writer", None)
        endpoint_health_manager = getattr(registry, "endpoint_health_manager", None)
        storage_backend_name = getattr(registry, "storage_backend_name", None)
        profile_config = getattr(registry, "profile_config", None)
        restart_on_threshold = (
            _to_bool(
                getattr(
                    profile_config.endpoint_health, "restart_on_threshold", None
                ),
                default=False,
            )
            if profile_config is not None
            else False
        )
        restart_exit_code = (
            _to_int(
                getattr(profile_config.endpoint_health, "restart_exit_code", None),
                default=75,
            )
            if profile_config is not None
            else 75
        )
        if (
            endpoint_health_manager is not None
            and storage_backend_name
            and profile_config is not None
            and tool_name != "backend_status"
        ):
            state = endpoint_health_manager.get_state(
                profile_name, storage_backend_name
            )
            if state is not None and state.status != "healthy":
                state = (
                    endpoint_health_manager.maybe_recover_backend(
                        profile_name=profile_name,
                        profile=profile_config,
                        backend_name=storage_backend_name,
                        logger=logger,
                    )
                    or state
                )
                if state.status != "healthy":
                    message = (
                        f"Backend unavailable: backend={storage_backend_name} "
                        f"status={state.status} reason={state.reason} "
                        f"requires_restart={state.requires_restart}"
                    )
                    if logger:
                        logger.warning(
                            message,
                            backend=storage_backend_name,
                            profile=profile_name,
                        )
                    if state.requires_restart and restart_on_threshold:
                        if logger:
                            logger.error(
                                "Endpoint restart threshold reached",
                                backend=storage_backend_name,
                                restart_exit_code=restart_exit_code,
                            )
                        raise SystemExit(restart_exit_code)
                    raise RuntimeError(message)
        if logger:
            logger.info(
                "tool_call",
                event="tool_call",
                profile=profile_name,
                tool=tool_name,
                params=params,
                correlation_id=get_correlation_id(),
                session_id=get_request_session_id(),
                client_ip=get_request_client_ip(),
            )
        try:
            result = raw_tool_handler(*args, **kwargs)
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            if logger:
                logger.info(
                    "tool_result",
                    event="tool_result",
                    profile=profile_name,
                    tool=tool_name,
                    outcome="ok",
                    duration_ms=elapsed_ms,
                    correlation_id=get_correlation_id(),
                    session_id=get_request_session_id(),
                    client_ip=get_request_client_ip(),
                )
            if audit_writer:
                audit_writer(
                    tool_name=tool_name,
                    action="tool_call",
                    status="ok",
                    outcome="ok",
                    params=params if isinstance(params, dict) else {},
                    duration_ms=elapsed_ms,
                    paths=paths,
                )
            return result
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            if logger:
                logger.info(
                    "tool_result",
                    event="tool_result",
                    profile=profile_name,
                    tool=tool_name,
                    outcome="error",
                    error=str(exc),
                    duration_ms=elapsed_ms,
                    correlation_id=get_correlation_id(),
                    session_id=get_request_session_id(),
                    client_ip=get_request_client_ip(),
                )
            if audit_writer:
                audit_writer(
                    tool_name=tool_name,
                    action="tool_call",
                    status="error",
                    outcome="error",
                    params=params if isinstance(params, dict) else {},
                    duration_ms=elapsed_ms,
                    paths=paths,
                    details={"error": str(exc)},
                )
            raise

    _sig_handler = registry_provider().get(tool_name).handler
    _base_sig = inspect.signature(_sig_handler)
    # W28C-1702 (FM3): advertise + accept an optional per-call ``profile`` selector.
    # normalize_and_filter_tool_args filters by THIS signature, so without adding
    # ``profile`` here the argument would be stripped before wrapped_handler runs.
    if "profile" not in _base_sig.parameters:
        _params = list(_base_sig.parameters.values())
        _profile_param = inspect.Parameter(
            "profile",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=Optional[str],
        )
        _var_kw_idx = next(
            (
                i
                for i, p in enumerate(_params)
                if p.kind == inspect.Parameter.VAR_KEYWORD
            ),
            None,
        )
        if _var_kw_idx is None:
            _params.append(_profile_param)
        else:
            _params.insert(_var_kw_idx, _profile_param)
        _base_sig = _base_sig.replace(parameters=_params)
    setattr(wrapped_handler, "__signature__", _base_sig)
    wrapped_handler.__name__ = f"wrapped_{tool_name}"
    wrapped_handler.__doc__ = f"Dynamic wrapper for tool {tool_name}"
    wrapped_handler.__annotations__ = getattr(_sig_handler, "__annotations__", {})
    wrapped_handler.__module__ = getattr(_sig_handler, "__module__", __name__)
    return wrapped_handler


def build_mcp_server(
    default_profile_name: str,
    config: ServerConfig,
    http: HttpRuntimeSettings,
    *,
    db_runtime: PlatformDatabaseRuntime | None = None,
    logger: LogLike | None = None,
    admin_identity_service: AdminIdentityService | None = None,
    jobs_runtime_factory: Callable[
        [ProfileConfig, str], FileMcpJobsRuntime | None
    ]
    | None = None,
) -> Any:
    """Build MCP HTTP ASGI bundle (cloud_dog_api_kit transport; W28A-742)."""
    if default_profile_name not in config.profiles:
        raise ValueError(f"Unknown default profile: {default_profile_name}")

    profile_auth = _build_profile_auth_map(config)
    for name, (resolved_keys, _, _) in profile_auth.items():
        if not resolved_keys:
            raise ValueError(f"No API keys configured for profile '{name}'")

    admin_api_keys: list[str] = []
    extra_admin_keys = str(read_env_var("FILE_MCP_ADMIN_API_KEYS") or "").strip()
    if extra_admin_keys:
        for candidate in extra_admin_keys.split(","):
            resolved = _resolve_auth_api_key_value(candidate)
            if resolved and resolved not in admin_api_keys:
                admin_api_keys.append(resolved)

    auth = MultiProfileApiKeyTokenVerifier(
        profile_auth,
        default_profile=default_profile_name,
        admin_api_keys=admin_api_keys,
        dynamic_key_resolver=(
            (
                lambda token, profile_name: admin_identity_service.resolve_dynamic_api_key(
                    token=token,
                    profile_name=profile_name,
                )
            )
            if admin_identity_service is not None
            else None
        ),
        audit_emitter=AuditEmitter(),
        logger=logger,
    )

    registry_lock = RLock()
    profiles_holder: dict[str, ProfileConfig] = dict(config.profiles)
    registry_by_profile: dict[str, ToolRegistry] = {}
    jobs_runtime_by_profile: dict[str, FileMcpJobsRuntime | None] = {}

    # --- W28A-1002-APPLY-A — CFG-06 A2A config-change event broadcaster ---
    # Shared platform primitive from cloud_dog_api_kit.a2a.events. Admin CRUD
    # closures call ``_publish_config_event`` after successful mutation so
    # downstream subscribers can track user/group/api_key/profile changes via
    # the ``/a2a/events`` SSE stream and ``/a2a/events/history`` endpoint
    # mounted by ``build_mcp_fastapi_application``.
    config_event_broadcaster = InMemoryEventBroadcaster()

    def _publish_config_event(
        *,
        resource: str,
        action: str,
        identifier: str,
        actor: Optional[str] = None,
        before: Optional[dict[str, Any]] = None,
        after: Optional[dict[str, Any]] = None,
        outcome: str = "success",
    ) -> None:
        """Publish a ConfigChangeEvent for an admin-CRUD operation.

        Synchronous wrapper: the broadcaster is async, so we schedule the
        publish on a running event loop when one is available; otherwise
        spin up ``asyncio.run`` for the duration of the publish call. In
        practice the MCP admin tools are dispatched from the HTTP server's
        event loop, so the running-loop path is the hot path.
        """
        try:
            event = ConfigChangeEvent(
                service="file-mcp-server",
                resource=resource,
                action=action,
                identifier=str(identifier or ""),
                actor=actor,
                before=before,
                after=after,
                outcome=outcome,
            )
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                # Hot path: schedule on the running loop without blocking.
                loop.create_task(config_event_broadcaster.publish(event))
            else:
                # Fallback (sync tool dispatched outside an event loop).
                asyncio.run(config_event_broadcaster.publish(event))
        except Exception as exc:  # noqa: BLE001 — publication must never break the CRUD op
            if logger is not None:
                logger.warning(
                    "Failed to publish config change event",
                    resource=resource,
                    action=action,
                    identifier=identifier,
                    error=str(exc),
                )

    def _jobs_runtime_provider(
        profile_name: str | None = None,
    ) -> FileMcpJobsRuntime | None:
        """Resolve jobs runtime for a profile."""
        selected_name = (
            str(profile_name or "").strip() or default_profile_name
        )
        with registry_lock:
            if selected_name in jobs_runtime_by_profile:
                return jobs_runtime_by_profile[selected_name]
            profile = profiles_holder.get(selected_name)
            if profile is None:
                profile = profiles_holder[default_profile_name]
                selected_name = default_profile_name
            runtime = (
                jobs_runtime_factory(profile, selected_name)
                if jobs_runtime_factory is not None
                else None
            )
            jobs_runtime_by_profile[selected_name] = runtime
            return runtime

    def _registry_provider(profile_name: str | None = None) -> ToolRegistry:
        """Resolve the per-profile tool registry.

        W28C-1702 (FM3): accept an explicit ``profile_name`` so a per-request
        ``profile`` tool argument can dispatch against the right backend. When
        omitted, fall back to the request-scoped profile (X-File-MCP-Profile
        header / context-var, FM4) then the default — preserving prior behaviour.
        """
        selected = (
            str(profile_name or "").strip()
            or get_request_profile_name(default_profile_name)
            or default_profile_name
        )
        with registry_lock:
            registry = registry_by_profile.get(selected)
            if registry is None:
                profile = profiles_holder.get(selected)
                if profile is None:
                    selected = default_profile_name
                    cached = registry_by_profile.get(selected)
                    if cached is not None:
                        return cached
                    profile = profiles_holder[default_profile_name]
                registry = build_tool_registry(
                    profile,
                    profile_name=selected,
                    logger=logger,
                    admin_identity_service=admin_identity_service,
                    jobs_runtime=_jobs_runtime_provider(selected),
                )
                registry_by_profile[selected] = registry
            return registry

    def _reload_registry(
        *, env_path: str | None, config_path: str | None, defaults_path: str | None
    ) -> dict[str, Any]:
        """Handle reload registry."""
        cfg = load_config(
            env_path=env_path, config_path=config_path, defaults_path=defaults_path
        )
        cfg = _merge_active_db_profiles_into_config(
            cfg,
            db_runtime=db_runtime,
            logger=logger,
        )
        with registry_lock:
            for runtime in jobs_runtime_by_profile.values():
                if runtime is not None:
                    runtime.close()
            jobs_runtime_by_profile.clear()
            profiles_holder.clear()
            profiles_holder.update(cfg.profiles)
            registry_by_profile.clear()
        # Refresh the auth verifier so dynamically created profiles are
        # routable via header/query-param/path profile selection.
        if hasattr(auth, "refresh_profiles") and callable(auth.refresh_profiles):
            refreshed_profile_auth = _build_profile_auth_map(cfg)
            if logger:
                logger.warning(
                    "Refreshing auth verifier profiles",
                    profile_count=len(refreshed_profile_auth),
                    profile_names=sorted(refreshed_profile_auth.keys())[:8],
                )
            auth.refresh_profiles(refreshed_profile_auth)
        for name, profile in cfg.profiles.items():
            ENDPOINT_HEALTH_MANAGER.run_startup_checks(
                profile_name=name, profile=profile, logger=logger
            )
        states = ENDPOINT_HEALTH_MANAGER.get_profile_states(default_profile_name)
        return {
            "profile": default_profile_name,
            "reloaded": True,
            "profiles": sorted(cfg.profiles.keys()),
            "endpoint_health": {
                name: state.__dict__.copy() for name, state in states.items()
            },
        }

    def _close_jobs_runtimes() -> None:
        """Close all active jobs backends."""
        with registry_lock:
            for runtime in jobs_runtime_by_profile.values():
                if runtime is not None:
                    runtime.close()
            jobs_runtime_by_profile.clear()

    from .mcp_api_kit_layer import build_mcp_fastapi_application

    def _profile_tool_factory(name: str) -> Callable[..., Any]:
        return create_profile_tool_handler(
            _registry_provider,
            name,
            default_profile_name=default_profile_name,
            logger=logger,
        )

    # PS-92 (W28A-970h-V2): read MCP + A2A base paths from config, fall back to
    # platform canonical defaults. `http.base_path` is a distinct transport-layer
    # concern and is NOT consulted here.
    _mcp_base_path = str(
        getattr(config.mcp_server, "base_path", None) or "/mcp"
    ).strip() or "/mcp"
    _a2a_base_path = str(
        getattr(config.a2a_server, "base_path", None) or "/a2a"
    ).strip() or "/a2a"
    mcp_app = build_mcp_fastapi_application(
        _registry_provider,
        auth,
        profile_tool_factory=_profile_tool_factory,
        web_session_store={},
        web_cookie_name="file_web_session",
        config_event_broadcaster=config_event_broadcaster,
        mcp_base_path=_mcp_base_path,
        a2a_base_path=_a2a_base_path,
    )
    server = SimpleNamespace()
    setattr(server, "_file_mcp_registry_provider", _registry_provider)
    setattr(server, "_file_mcp_reload_registry", _reload_registry)
    setattr(server, "_file_mcp_auth_verifier", auth)
    setattr(server, "_file_mcp_jobs_runtime_provider", _jobs_runtime_provider)
    setattr(server, "_file_mcp_jobs_runtime_close_all", _close_jobs_runtimes)
    setattr(server, "_file_mcp_asgi_app", mcp_app)
    # W28A-1002-APPLY-A — expose broadcaster for tests + external publishers.
    setattr(server, "_file_mcp_config_event_broadcaster", config_event_broadcaster)
    return server


async def run_mcp_http_server(
    *,
    default_profile_name: str,
    config: ServerConfig,
    http_config: HttpServerConfig,
    logger: LogLike | None = None,
) -> None:
    # Instantiate API-kit app config for PS-20 contract alignment and dependency verification.
    """Execute run MCP HTTP server."""
    create_api_kit_app(
        title="file-mcp-server",
        version="0.0.0",
        enable_docs=False,
        enable_cors=False,
        enable_request_logging=False,
        register_signal_handlers_on_startup=False,
    )

    db_runtime = initialise_database()
    admin_identity_service = AdminIdentityService(
        session_manager=db_runtime.session_manager,
        logger=logger,
    )
    admin_identity_service.ensure_bootstrap_seed(
        username=str(read_env_var("CLOUD_DOG_WEB_LOGIN_USERNAME") or "admin")
    )

    # --- Phase 4b: Seed default profile into DB on first startup ---
    with db_runtime.session_manager.session() as _seed_session:
        _db_profile_count = _seed_session.query(FileStorageProfile).filter_by(is_active=True).count()
        if _db_profile_count == 0:
            for _cfg_name, _cfg_profile in config.profiles.items():
                _cfg_dict = _cfg_profile.model_dump(mode="json")
                _backend = str(_cfg_profile.storage.backend) if _cfg_profile.storage else "local"
                _seed_row = FileStorageProfile(
                    id=f"prof_{uuid.uuid4().hex[:12]}",
                    name=_cfg_name,
                    display_name=_cfg_name,
                    backend=_backend,
                    config_json=json.dumps(_cfg_dict),
                    is_active=True,
                )
                _seed_session.add(_seed_row)
            _seed_session.commit()
            if logger:
                logger.info(
                    "Seeded database with config profiles",
                    profile_count=len(config.profiles),
                    profile_names=sorted(config.profiles.keys()),
                )

    # --- Phase 4: Load DB profiles and merge (DB takes precedence) ---
    config = _merge_active_db_profiles_into_config(
        config,
        db_runtime=db_runtime,
        logger=logger,
    )

    # W28C-1702 (FM5): republish the active-profile env to the DB-MERGED set so
    # /status.service_metrics.profile_count and FILE_MCP_ACTIVE_PROFILE_NAMES agree.
    # main.py set this var from the config-FILE profiles BEFORE this merge, which
    # collapsed it to "default" (profile_count read 1 against ~10 active profiles).
    # This is a WRITE (publish), not a cloud_dog_config bypass — RULES §1.4.1
    # targets env *reads*; os.environ.update is used as the write API.
    os.environ.update(
        {"FILE_MCP_ACTIVE_PROFILE_NAMES": ",".join(config.profiles.keys())}
    )

    # Ensure the default profile exists after merge
    if default_profile_name not in config.profiles:
        if logger:
            logger.error(
                "Default profile not found after DB merge",
                default_profile=default_profile_name,
                available=sorted(config.profiles.keys()),
            )

    db_sync_url = db_runtime.settings.to_sync_url()
    http = resolve_http_settings(http_config)
    for profile_name, profile in config.profiles.items():
        ENDPOINT_HEALTH_MANAGER.run_startup_checks(
            profile_name=profile_name, profile=profile, logger=logger
        )
        if _to_bool(profile.endpoint_health.restart_on_threshold, default=False):
            exit_code = _to_int(profile.endpoint_health.restart_exit_code, default=75)
            states = ENDPOINT_HEALTH_MANAGER.get_profile_states(profile_name)
            for state in states.values():
                if state.requires_restart:
                    if logger:
                        logger.error(
                            "Endpoint startup health exceeded restart threshold",
                            profile=profile_name,
                            backend=state.backend,
                            restart_exit_code=exit_code,
                        )
                    raise SystemExit(exit_code)
    server = build_mcp_server(
        default_profile_name,
        config,
        http,
        db_runtime=db_runtime,
        logger=logger,
        admin_identity_service=admin_identity_service,
        jobs_runtime_factory=(
            lambda profile, profile_name: FileMcpJobsRuntime.from_profile(
                profile,
                profile_name=profile_name,
                fallback_sql_url=db_sync_url,
            )
        ),
    )
    reload_fn = getattr(server, "_file_mcp_reload_registry", None)
    registry_provider = getattr(server, "_file_mcp_registry_provider", None)
    auth_verifier = getattr(server, "_file_mcp_auth_verifier", None)
    jobs_runtime_provider = getattr(server, "_file_mcp_jobs_runtime_provider", None)
    jobs_runtime_close_all = getattr(server, "_file_mcp_jobs_runtime_close_all", None)
    env_path = read_env_var("FILE_MCP_ACTIVE_ENV_PATH") or None
    config_path = read_env_var("FILE_MCP_ACTIVE_CONFIG_PATH") or None
    defaults_path = read_env_var("FILE_MCP_ACTIVE_DEFAULTS_PATH") or None

    def _reload_callback():
        """Handle reload callback."""
        if not callable(reload_fn):
            raise RuntimeError("reload function unavailable")
        return reload_fn(
            env_path=env_path, config_path=config_path, defaults_path=defaults_path
        )

    mcp_inner = getattr(server, "_file_mcp_asgi_app", None)
    if mcp_inner is None:
        raise RuntimeError("MCP ASGI application not built")
    shared_web_sessions = getattr(mcp_inner.state, "file_mcp_web_sessions", None)
    # W28A-1002-APPLY-A — CFG-06: share the broadcaster between MCP tool CRUD
    # and the HTTP /admin/* CRUD endpoints handled by HealthCheckMiddleware.
    shared_event_broadcaster = getattr(
        server, "_file_mcp_config_event_broadcaster", None
    )
    hc_app = HealthCheckMiddleware(
        mcp_inner,
        health_path=http.health_path,
        profile_name=default_profile_name,
        transport=http.transport,
        config=config,
        reload_callback=_reload_callback,
        registry_provider=registry_provider,
        mcp_path=http.mcp_path,
        a2a_auth_verifier=auth_verifier,
        db_runtime=db_runtime,
        admin_identity_service=admin_identity_service,
        jobs_runtime_provider=jobs_runtime_provider,
        callback_host_fallback=http.host,
        web_sessions=shared_web_sessions,
        cookie_name="file_web_session",
        config_event_broadcaster=shared_event_broadcaster,
    )
    stream_app = StreamableHttpAcceptCompatibilityMiddleware(
        hc_app,
        mcp_path=http.mcp_path,
    )
    asgi_app = RequestContextMiddleware(stream_app)
    endpoint_path = http.events_path if http.transport == "sse" else http.mcp_path
    if logger:
        logger.info(
            "Starting MCP HTTP (cloud_dog_api_kit)",
            transport=http.transport,
            host=http.host,
            port=http.port,
            endpoint=endpoint_path,
            health=http.health_path,
        )

    try:
        uvconfig = uvicorn.Config(
            asgi_app,
            host=str(http.host),
            port=int(http.port),
            log_level="info",
        )
        uvserver = uvicorn.Server(uvconfig)
        await uvserver.serve()
    finally:
        if callable(jobs_runtime_close_all):
            jobs_runtime_close_all()
        shutdown_database()
# W28A-565 cache bust 1775026097
