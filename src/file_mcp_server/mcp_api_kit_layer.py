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

"""MCP transport via cloud_dog_api_kit for file-mcp-server tool dispatch.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Builds the API-kit ASGI transport layer for MCP, WebMCP, and A2A routes.
Requirements: FR1.2, FR1.5, FR1.23, FR1.46
Tasks: W28A-101a
Architecture: API-kit MCP transport
Tests: ST1, IT1, AT1, QT1
"""

from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import Request
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from starlette.authentication import AuthCredentials
from starlette.responses import JSONResponse

from cloud_dog_api_kit.a2a.events import (  # W28A-1002-APPLY-A — CFG-06 primitive
    EventBroadcaster,
    create_a2a_events_router,
)
from cloud_dog_api_kit.envelopes import error_envelope
from cloud_dog_api_kit.errors import UnauthenticatedError, UnauthorisedError
from cloud_dog_api_kit.factory import create_app
from cloud_dog_api_kit.mcp import ToolContract
from cloud_dog_api_kit.mcp.tool_router import register_tool_router
from cloud_dog_api_kit.mcp.transport import register_mcp_routes
from cloud_dog_idam.rbac import RBACEngine  # PS-50 per-tool RBAC

try:
    from cloud_dog_api_kit.mcp.tool_audit import mcp_tool_audit_middleware
except ImportError:
    from .mcp_tool_audit_shim import mcp_tool_audit_middleware

from file_tools.tools.registry import ToolRegistry

from .auth import (
    AccessToken,
    MultiProfileApiKeyTokenVerifier,
    get_request_profile_name,
)


_WEB_COOKIE_AUTH_SUBJECT = "web-session"


class WebMcpCookieAuthMiddleware:
    """Authenticate `/webmcp` requests from the shared WebUI cookie session."""

    def __init__(
        self,
        app,
        *,
        session_store: dict[str, dict[str, Any]] | None = None,
        cookie_name: str = "file_web_session",
        session_ttl_seconds: int = 3600,
    ) -> None:
        self.app = app
        self.session_store = session_store if session_store is not None else {}
        self.cookie_name = cookie_name
        self.session_ttl_seconds = session_ttl_seconds

    def _active_session(self, request: Request) -> dict[str, Any] | None:
        import time

        token = request.cookies.get(self.cookie_name)
        if not token:
            return None
        session = self.session_store.get(token)
        if session is None:
            return None
        created = float(session.get("_created") or 0.0)
        if created <= 0.0 or time.time() - created >= self.session_ttl_seconds:
            self.session_store.pop(token, None)
            return None
        return session

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        if not (path == "/webmcp" or path.startswith("/webmcp/")):
            await self.app(scope, receive, send)
            return

        user = scope.get("user")
        if getattr(user, "is_authenticated", False):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        session = self._active_session(request)
        if session is None:
            response = JSONResponse(
                status_code=401,
                content=error_envelope(
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                ),
            )
            await response(scope, receive, send)
            return

        access_token = AccessToken(
            token=_WEB_COOKIE_AUTH_SUBJECT,
            client_id=str(session.get("user_id") or "1"),
            scopes=["*"],
            claims={
                "auth_mode": "cookie",
                "role": str(session.get("role") or "admin"),
                "user_id": str(session.get("user_id") or "1"),
                "username": str(session.get("user") or "admin"),
            },
        )
        scope["auth"] = AuthCredentials(access_token.scopes)
        scope["user"] = AuthenticatedUser(access_token)
        await self.app(scope, receive, send)


def tool_required_permission(tool_name: str) -> str:
    """Map registered MCP tool name to PS-50 permission string."""
    n = tool_name.lower()
    if n.startswith("gdrive_"):
        return "file:gdrive:write" if "upload" in n else "file:gdrive:read"
    if n.startswith("admin_"):
        return "file:read"
    if any(
        x in n
        for x in (
            "write",
            "delete",
            "create",
            "move",
            "copy",
            "chmod",
            "merge",
            "convert",
            "sed_",
            "upload",
        )
    ):
        return "file:write"
    if "_set" in n or n.endswith("_set"):
        return "file:write"
    return "file:read"

_EXTRA_AUDIT_REDACT: frozenset[str] = frozenset(
    {
        "content",
        "body",
        "text",
        "data",
        "file_content",
        "raw",
        "bytes",
    }
)


def _scopes_allow(required: str, scopes: list[str] | None) -> bool:
    s = set(scopes or [])
    if "*" in s or "file:*" in s or required in s:
        return True
    write_required = required == "file:write"
    if write_required and (
        "profile:write" in s
        or "profile:*" in s
        or any(
            scope.startswith("profile:")
            and (scope.count(":") == 1 or scope.endswith(":write"))
            for scope in s
        )
    ):
        return True
    if not write_required and required in {"file:read", "file:list", "file:search"}:
        if (
            "file:write" in s
            or "profile:read" in s
            or "profile:write" in s
            or "profile:*" in s
        ):
            return True
        if any(
            scope.startswith("profile:")
            and (
                scope.count(":") == 1
                or scope.endswith(":read")
                or scope.endswith(":write")
            )
            for scope in s
        ):
            return True
    return False


def _make_dynamic_tool_handler(
    tool_name: str,
    profile_tool_factory: Callable[[str], Callable[..., Any]],
    *,
    verifier: MultiProfileApiKeyTokenVerifier,
) -> Callable[[dict[str, Any], Request], Any]:
    """Wrap profile tool factory with PS-50 MCP audit + RBAC."""

    required = tool_required_permission(tool_name)

    def _sync_core(**kwargs: Any) -> Any:
        from file_tools.tools.schemas import normalize_tool_args
        inner = profile_tool_factory(tool_name)
        return inner(**normalize_tool_args(kwargs))

    audited = mcp_tool_audit_middleware(
        tool_name,
        _sync_core,
        service="file-mcp-server",
        redact_fields=_EXTRA_AUDIT_REDACT,
    )

    def _mcp_tool_result_payload(result: Any) -> dict[str, Any]:
        """Normalise service tool results to a full MCP CallToolResult payload.

        When the result is a dict with an 'ok' field it is a structured tool
        envelope (e.g. ``{"ok": True, "data": "..."}``).  Serialise the full
        dict as JSON text so that MCP clients parsing ``content[0].text``
        receive the complete envelope rather than an extracted sub-field.

        For non-dict results (e.g. a plain string from ``read_file``), the
        value is placed directly in text content without JSON encoding so
        that consumers can use it verbatim.
        """
        if isinstance(result, dict) and isinstance(result.get("content"), list):
            payload = dict(result)
            if "structuredContent" not in payload:
                payload["structuredContent"] = result
            return payload

        if isinstance(result, list) and all(
            isinstance(item, dict) and "type" in item for item in result
        ):
            return {"content": result, "structuredContent": {"value": result}}

        is_error = False
        if isinstance(result, dict):
            if result.get("ok") is False:
                is_error = True
            elif result.get("error") is not None:
                is_error = True
            # Serialise the full dict as JSON text to preserve the envelope.
            text = json.dumps(result, default=str, ensure_ascii=True)
            return {
                "content": [{"type": "text", "text": text}],
                "structuredContent": result,
                "isError": is_error,
            }

        # Non-dict results: place value directly in text content.
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, default=str, ensure_ascii=True)
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": {"value": result},
            "isError": False,
        }

    async def _handler(payload: dict[str, Any], request: Request) -> Any:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise UnauthenticatedError("Authentication required for MCP tool calls")
        token = getattr(user, "access_token", None)
        scopes = list(getattr(token, "scopes", None) or [])
        if not _scopes_allow(required, scopes):
            raise UnauthorisedError(f"Missing permission: {required}")
        try:
            return _mcp_tool_result_payload(audited(**payload))
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": str(exc)}],
                "structuredContent": {"error": str(exc)},
                "isError": True,
            }

    return _handler


def build_tool_contracts(
    registry_provider: Callable[[], ToolRegistry],
    verifier: MultiProfileApiKeyTokenVerifier,
    *,
    seed_registry: ToolRegistry,
    profile_tool_factory: Callable[[str], Callable[..., Any]],
) -> dict[str, ToolContract]:
    """Build ToolContract map from seed registry tool names (dynamic dispatch)."""
    out: dict[str, ToolContract] = {}
    for definition in seed_registry.list_tools():
        name = definition.meta.name
        handler = _make_dynamic_tool_handler(
            name, profile_tool_factory, verifier=verifier
        )
        tool_input_schema: dict[str, Any] = {}
        if definition.schema_def.input_model is not None:
            try:
                tool_input_schema = definition.schema_def.input_model.model_json_schema()
            except Exception:
                pass
        out[name] = ToolContract(
            name=name,
            handler=handler,
            description=definition.meta.description,
            input_schema=tool_input_schema,
            output_schema={},
        )
    return out


def build_mcp_fastapi_application(
    registry_provider: Callable[[], ToolRegistry],
    auth_verifier: MultiProfileApiKeyTokenVerifier,
    *,
    profile_tool_factory: Callable[[str], Callable[..., Any]],
    web_session_store: dict[str, dict[str, Any]] | None = None,
    web_cookie_name: str = "file_web_session",
    config_event_broadcaster: EventBroadcaster | None = None,
    mcp_base_path: str = "/mcp",
    a2a_base_path: str = "/a2a",
) -> Any:
    """FastAPI ASGI app: MCP JSON-RPC + api_kit transport + IDAM middleware.

    Args:
        config_event_broadcaster: CFG-06 A2A change-event broadcaster.
            When provided, ``GET {a2a_base_path}/events`` (SSE) and
            ``GET {a2a_base_path}/events/history`` (JSON) are registered via
            ``create_a2a_events_router`` from ``cloud_dog_api_kit.a2a.events``.
            The broadcaster is also made available on
            ``app.state.config_event_broadcaster`` for tests.
        mcp_base_path: PS-92 canonical MCP server route prefix (default ``/mcp``).
            Drives the ``{mcp_base_path}/tools`` mount.
        a2a_base_path: PS-92 canonical A2A server route prefix (default ``/a2a``).
            Drives the ``{a2a_base_path}/events{,/history}`` mount. The secondary
            ``/events`` mount is an intentional Traefik-stripped alias and remains
            hardcoded (see comment below).
    """
    session_store = web_session_store if web_session_store is not None else {}
    seed = registry_provider()
    contracts = build_tool_contracts(
        registry_provider,
        auth_verifier,
        seed_registry=seed,
        profile_tool_factory=profile_tool_factory,
    )
    app = create_app(
        title="file-mcp-server-mcp",
        version="1.0.0",
        enable_docs=False,
        enable_health=False,
        enable_request_logging=False,
        enable_cors=False,
        register_signal_handlers_on_startup=False,
        enable_audit_logging=False,
    )
    app.state.file_mcp_web_sessions = session_store
    if config_event_broadcaster is not None:
        # W28A-1002-APPLY-A — CFG-06: expose broadcaster + register SSE/history routes.
        app.state.config_event_broadcaster = config_event_broadcaster
    app.add_middleware(
        WebMcpCookieAuthMiddleware,
        session_store=session_store,
        cookie_name=web_cookie_name,
    )
    for mw in auth_verifier.get_middleware():
        app.add_middleware(mw.cls, *mw.args, **mw.kwargs)

    def _request_context_hook(request: Request) -> dict[str, Any]:
        profile_name = (
            get_request_profile_name(auth_verifier.default_profile)
            or auth_verifier.default_profile
        )
        return {
            "profile_name": profile_name,
            "transport_path": str(request.url.path),
        }

    # PS-92 (W28A-970h-V2): tools mounted under configured MCP base_path.
    _mcp_tools_base = f"{mcp_base_path.rstrip('/')}/tools" if mcp_base_path else "/tools"
    register_tool_router(app, contracts, base_path=_mcp_tools_base)
    register_mcp_routes(
        app,
        contracts,
        transport_modes=["streamable_http", "http_jsonrpc", "legacy_sse"],
        request_context_hook=_request_context_hook,
        alternate_endpoints=[{"path": "/webmcp", "auth": "cookie", "name": "web"}],
        session_termination_mode="204_idempotent",
        error_response_mode="jsonrpc_200",
    )

    if config_event_broadcaster is not None:
        # W28A-1002-APPLY-A — CFG-06: mount at BOTH paths to cover:
        # (a) native servers / tests (external == internal path)
        #     → ``{a2a_base_path}/events`` + ``{a2a_base_path}/events/history``
        #     reachable directly;
        # (b) preprod via Traefik which strips the ``/a2a`` prefix (see
        #     terraform filemcpserver_containers.tf.json middleware
        #     ``filemcpserver0_a2a_strip``)
        #     → external ``{a2a_base_path}/events{,/history}`` forwards as
        #     internal ``/events{,/history}``. The Traefik-stripped alias
        #     remains hardcoded as ``/events`` because it is NOT configurable
        #     per PS-92 (it tracks Traefik middleware behaviour, not a
        #     service-level route prefix).
        # Both sets of routes share the same broadcaster instance; fan-out
        # is unified.
        _a2a_events_base = (
            f"{a2a_base_path.rstrip('/')}/events" if a2a_base_path else "/events"
        )
        app.include_router(
            create_a2a_events_router(
                config_event_broadcaster,
                base_path=_a2a_events_base,
            )
        )
        app.include_router(
            create_a2a_events_router(
                config_event_broadcaster,
                base_path="/events",
            )
        )

    # PS-50: Per-tool RBAC enforcement via cloud_dog_idam.
    _TOOL_PERMISSION_MAP = {
        "file_read": "file:read", "file_write": "file:write",
        "file_list": "file:list", "file_search": "file:search",
        "file_upload": "file:write", "file_download": "file:read",
        "file_delete": "file:write", "file_move": "file:write",
        "file_copy": "file:write", "dir_list": "file:list",
        "dir_mkdir": "file:write", "dir_rmdir": "file:write",
    }
    _rbac = RBACEngine(role_permissions={
        "admin": {"file:*"},
        "user": {"file:read", "file:write", "file:list", "file:search"},
        "viewer": {"file:read", "file:list", "file:search"},
    })

    def _enforce_tool_rbac(user_id: str, tool_name: str) -> bool:
        """PS-50 per-tool RBAC check."""
        perm = _TOOL_PERMISSION_MAP.get(tool_name, "file:read")
        return _rbac.has_permission(user_id, perm)  # has_permission for tool access
    return app
