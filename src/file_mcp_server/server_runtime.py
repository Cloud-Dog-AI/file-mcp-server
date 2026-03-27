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

from dataclasses import dataclass
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional, Protocol, TextIO, cast
from threading import RLock
from html import escape

import inspect
import json
import mimetypes
import secrets
import sys
import time
import uuid
from urllib.parse import parse_qs
import re
from os import getenv as read_env_var

from fastmcp import FastMCP
from cloud_dog_api_kit import create_app as create_api_kit_app, create_health_router  # type: ignore[import-not-found,import-untyped]
from cloud_dog_idam.audit.emitter import AuditEmitter  # type: ignore[import-not-found,import-untyped]
from cloud_dog_config.compiler.evaluator import (  # type: ignore[import-untyped]
    SafeExpressionError,
    Unresolved,
    evaluate,
)
from cloud_dog_config.compiler.vault_resolver import (  # type: ignore[import-untyped]
    resolve_vault_identifier,
)
from cloud_dog_config.vault.client import (  # type: ignore[import-untyped]
    VaultClient,
    VaultConnectionConfig,
)
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
from file_tools.convert import (
    BackendCannotHandleError,
    BackendNotFoundError,
    BackendUnavailableError,
    ConversionError,
    convert_file as run_convert_file,
)
from file_tools.limits import LimitError, enforce_timeout
from file_tools.validate.policy import validate_with_mode
from file_tools.adapters.yaml_codec import safe_dump
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection
from mcp.server.auth.middleware.auth_context import get_access_token

from .idam_adapter import MultiProfileApiKeyTokenVerifier, get_request_profile_name
from .endpoint_health import ENDPOINT_HEALTH_MANAGER
from .db import (
    PlatformDatabaseRuntime,
    database_health,
    initialise_database,
    shutdown_database,
)
from .jobs_runtime import FileMcpJobsRuntime
from .google_drive_admin import (
    MASKED_CLIENT_SECRET,
    begin_oauth,
    complete_oauth_callback,
    parse_form_urlencoded,
    render_setup_page,
)
from .admin_identity import AdminIdentityError, AdminIdentityService

OOB_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
_REQUEST_SESSION_ID: ContextVar[str | None] = ContextVar(
    "file_mcp_request_session_id", default=None
)
_REQUEST_CLIENT_IP: ContextVar[str | None] = ContextVar(
    "file_mcp_request_client_ip", default=None
)


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


def _build_runtime_vault_client() -> VaultClient | None:
    """Build a Vault client from current runtime environment."""
    server = str(read_env_var("VAULT_ADDR", "")).strip()
    token = str(read_env_var("VAULT_TOKEN", "")).strip()
    mount_point = str(read_env_var("VAULT_MOUNT_POINT", "")).strip()
    if not server or not token:
        return None
    try:
        return VaultClient(
            VaultConnectionConfig(
                server=server,
                token=token,
                mount_point=mount_point,
            )
        )
    except Exception:
        return None


def _resolve_runtime_expression(
    expression: str, *, vault_client: VaultClient | None
) -> str:
    """Resolve a single `${...}` expression using env and optional Vault."""

    def _resolve_identifier(identifier: str) -> Any:
        token = str(identifier).strip()
        if not token:
            return Unresolved(token)
        if token.startswith("vault."):
            if vault_client is None:
                return Unresolved(token)
            try:
                return resolve_vault_identifier(token, vault=vault_client)
            except Exception:
                return Unresolved(token)

        env_value = read_env_var(token)
        if env_value is None:
            return Unresolved(token)
        value = str(env_value).strip()
        if not value:
            return Unresolved(token)
        return value

    try:
        resolved = evaluate(expression, _resolve_identifier)
    except SafeExpressionError:
        return ""

    if isinstance(resolved, Unresolved):
        return ""
    if isinstance(resolved, (dict, list, tuple, set)):
        return ""
    return str(resolved).strip()


def _resolve_auth_api_key_value(
    raw_value: str, *, vault_client: VaultClient | None
) -> str:
    """Resolve nested placeholder forms used for API-key entries."""
    value = str(raw_value or "").strip()
    if not value:
        return ""

    for _ in range(4):
        match = re.fullmatch(r"\$\{(.+)\}", value)
        if not match:
            break
        resolved = _resolve_runtime_expression(
            match.group(1).strip(), vault_client=vault_client
        )
        if not resolved or resolved == value:
            break
        value = resolved.strip()

    if "${" in value:
        return ""
    return value


def _build_profile_auth_map(
    config: ServerConfig,
) -> dict[str, tuple[list[str], str | None, str | None]]:
    """Build per-profile auth mapping with resolved API-key values."""
    vault_client = _build_runtime_vault_client()
    profile_auth: dict[str, tuple[list[str], str | None, str | None]] = {}
    for name, profile in config.profiles.items():
        resolved_keys = [
            resolved
            for resolved in (
                _resolve_auth_api_key_value(str(item), vault_client=vault_client)
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
                tools = [
                    {
                        "name": tool.meta.name,
                        "description": tool.meta.description,
                        "mutating": tool.meta.mutating,
                        "requires_validation": tool.meta.requires_validation,
                        "supports_dry_run": tool.meta.supports_dry_run,
                    }
                    for tool in self.registry.list_tools()
                ]
                return _build_response(request_id, result=tools)
            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not name:
                    raise DispatchError("Missing tool name")
                tool = self.registry.get(name)
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


class HealthCheckMiddleware:
    """Minimal unauthenticated health endpoint for transport app."""

    def __init__(
        self,
        app,
        *,
        health_path: str,
        profile_name: str,
        transport: str,
        reload_callback=None,
        registry_provider=None,
        mcp_path: str = "/mcp",
        a2a_auth_verifier=None,
        db_runtime: PlatformDatabaseRuntime | None = None,
        admin_identity_service: AdminIdentityService | None = None,
        jobs_runtime_provider: Callable[[str | None], FileMcpJobsRuntime | None]
        | None = None,
        callback_host_fallback: str = "",
    ) -> None:
        """Initialise the instance state."""
        self.app = app
        self.health_path = health_path
        self.profile_name = profile_name
        self.transport = transport
        self.reload_callback = reload_callback
        self.registry_provider = registry_provider
        self.mcp_path = _normalize_path(mcp_path, default="/mcp")
        self.a2a_auth_verifier = a2a_auth_verifier
        self.db_runtime = db_runtime
        # Session store for cookie-based WebUI login.
        self._sessions: dict[str, dict] = {}
        self._admin_username = read_env_var("CLOUD_DOG_WEB_LOGIN_USERNAME") or "admin"
        self._admin_password = read_env_var("CLOUD_DOG_WEB_LOGIN_PASSWORD") or ""
        self._cookie_name = "file_web_session"
        self.admin_identity_service = admin_identity_service
        self.jobs_runtime_provider = jobs_runtime_provider
        self.a2a_base_path = _normalize_path(
            read_env_var("TEST_A2A_BASE_PATH"), default="/a2a"
        )
        self.a2a_health_path = _join_paths(self.a2a_base_path, "/health")
        self.logger = get_logger("file_mcp_server.admin")
        self.app_name = "file-mcp-server"
        self.version = str(read_env_var("FILE_MCP_VERSION") or "0.0.0").strip() or "0.0.0"
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
        self.admin_ui_enabled = _to_bool(
            read_env_var("FILE_MCP_ADMIN_UI_ENABLED"), default=False
        )
        self.admin_ui_token = str(read_env_var("FILE_MCP_ADMIN_UI_TOKEN") or "").strip()
        self.admin_apply_on_callback = _to_bool(
            read_env_var("FILE_MCP_ADMIN_APPLY_ON_CALLBACK"), default=True
        )
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
        configured_ui_dist = str(read_env_var("FILE_MCP_UI_DIST_PATH") or "").strip()
        if configured_ui_dist:
            self.ui_dist_path = Path(configured_ui_dist).expanduser().resolve()
        else:
            self.ui_dist_path = (
                Path(__file__).resolve().parents[2] / "ui" / "dist"
            ).resolve()

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

    def _list_tools_payload(self) -> dict[str, Any]:
        """Handle list tools payload."""
        if not callable(self.registry_provider):
            return {"tools": []}
        registry = self.registry_provider()
        tools = [
            {
                "name": tool.meta.name,
                "description": tool.meta.description,
                "mutating": tool.meta.mutating,
                "requires_validation": tool.meta.requires_validation,
                "supports_dry_run": tool.meta.supports_dry_run,
            }
            for tool in registry.list_tools()
        ]
        return {"tools": tools}

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
        if username != self._admin_username or password != self._admin_password:
            await self._send_bytes(send, status=401, body=b'{"detail":"Invalid credentials"}', content_type="application/json")
            return True
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {"user": username, "user_id": "1", "role": "admin", "_created": _time.time()}
        resp_body = json.dumps({"user": {"id": "1", "displayName": username, "email": None, "roles": ["admin"], "permissions": ["*"]}}).encode("utf-8")
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

    async def _handle_auth_me(self, send, headers: dict[str, str]) -> bool:
        """Handle GET /auth/me — return current session user."""
        sess = self._get_session_from_cookie(headers)
        if not sess:
            await self._send_bytes(send, status=401, body=b'{"detail":"Not authenticated"}', content_type="application/json")
            return True
        resp_body = json.dumps({"user": {"id": sess["user_id"], "displayName": sess["user"], "email": None, "roles": [sess["role"]], "permissions": ["*"]}}).encode("utf-8")
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
    ) -> None:
        """Handle send bytes."""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", content_type.encode("utf-8")),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

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

    async def _send_redirect(self, send, *, location: str) -> None:
        """Handle send redirect."""
        await send(
            {
                "type": "http.response.start",
                "status": 302,
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
            "/file-browser",
            "/search",
            "/storage-profiles",
            "/audit-log",
            "/admin-identity",
            "/admin/identity",
            "/admin/rbac",
            "/google-drive-settings",
            "/settings",
        )

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

        candidate = (self.ui_dist_path / relative_path).resolve()
        try:
            candidate.relative_to(self.ui_dist_path)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return candidate

    async def _send_file(self, send, *, path: Path, method: str) -> None:
        """Send a file response for GET/HEAD requests."""
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
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

        audit_log_path = (
            str(read_env_var("FILE_MCP_UI_AUDIT_LOG_PATH") or "").strip()
            or "working/test-env-st/audit.log.jsonl"
        )
        default_browse_path = (
            str(read_env_var("FILE_MCP_UI_DEFAULT_BROWSE_PATH") or "").strip() or "src"
        )
        profile_store_path = (
            str(read_env_var("FILE_MCP_UI_PROFILE_STORE_PATH") or "").strip()
            or "working/ui-file-mcp/storage-profiles.json"
        )

        return {
            "ENV": env_name,
            "API_BASE_URL": api_base_url,
            "AUTH_MODE": auth_mode,
            "AUDIT_LOG_PATH": audit_log_path,
            "DEFAULT_BROWSE_PATH": default_browse_path,
            "PROFILE_STORE_PATH": profile_store_path,
        }

    async def _serve_runtime_config(self, send, *, method: str) -> None:
        """Serve runtime configuration bootstrap JavaScript.

        Uses JavaScript expression for API_BASE_URL so the browser resolves
        the correct protocol behind a reverse proxy (Traefik / HTTPS).
        """
        payload = self._runtime_config_payload()
        lines = [
            "const __origin = window.location.origin;",
            "window.__RUNTIME_CONFIG__ = {",
            f"  ENV: {json.dumps(payload.get('ENV', 'dev'))},",
            "  API_BASE_URL: __origin,",
            f"  AUTH_MODE: {json.dumps(payload.get('AUTH_MODE', 'api_key'))},",
            f"  AUDIT_LOG_PATH: {json.dumps(payload.get('AUDIT_LOG_PATH', ''))},",
            f"  DEFAULT_BROWSE_PATH: {json.dumps(payload.get('DEFAULT_BROWSE_PATH', 'src'))},",
            f"  PROFILE_STORE_PATH: {json.dumps(payload.get('PROFILE_STORE_PATH', ''))},",
            "};",
        ]
        script = ("\n".join(lines) + "\n").encode("utf-8")
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
        if not index_path.is_file():
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

    def _load_config_document(self) -> dict[str, Any]:
        """Load active config YAML as mutable dictionary."""
        config_path = Path(self.active_config)
        if not config_path.exists():
            return {"profiles": {}}
        try:
            parsed = load_yaml(str(config_path), missing_ok=True)
        except Exception:
            return {"profiles": {}}
        if not isinstance(parsed, dict):
            return {"profiles": {}}
        if not isinstance(parsed.get("profiles"), dict):
            parsed["profiles"] = {}
        return parsed

    def _write_config_document(self, document: dict[str, Any]) -> None:
        """Persist active config YAML document."""
        config_path = Path(self.active_config)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            safe_dump(document, sort_keys=False),
            encoding="utf-8",
        )

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
            folder_url = self._configured_value(drive.folder_url)
            folder_id = self._configured_value(drive.folder_id)
            configured_redirect = self._configured_value(drive.redirect_uri)
            redirect_uri = (
                callback_url
                if configured_redirect.strip().lower() == OOB_REDIRECT_URI
                else (configured_redirect or callback_url)
            )
            return {
                "user_email": self._configured_value(drive.user_email),
                "folder_input": folder_url or folder_id,
                "client_id": self._configured_value(drive.client_id),
                "client_secret": self._configured_value(drive.client_secret),
                "folder_url_example": self._configured_value(drive.folder_url_example),
                "oauth_scope": self._configured_value(drive.oauth_scope),
                "oauth_authorize_uri": self._configured_value(
                    drive.oauth_authorize_uri
                ),
                "api_base_uri": self._configured_value(drive.api_base_uri),
                "redirect_uri": redirect_uri,
                "token_uri": self._configured_value(drive.token_uri),
            }
        except Exception:
            config_path = Path(self.active_config)
            if not config_path.exists():
                return empty_values
            try:
                parsed = load_yaml(str(config_path), missing_ok=True)
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

                folder_url = self._configured_value(raw_drive.get("folder_url"))
                folder_id = self._configured_value(raw_drive.get("folder_id"))
                configured_redirect = self._configured_value(
                    raw_drive.get("redirect_uri")
                )
                redirect_uri = (
                    callback_url
                    if configured_redirect.strip().lower() == OOB_REDIRECT_URI
                    else (configured_redirect or callback_url)
                )
                return {
                    "user_email": self._configured_value(raw_drive.get("user_email")),
                    "folder_input": folder_url or folder_id,
                    "client_id": self._configured_value(raw_drive.get("client_id")),
                    "client_secret": self._configured_value(
                        raw_drive.get("client_secret")
                    ),
                    "folder_url_example": self._configured_value(
                        raw_drive.get("folder_url_example")
                    ),
                    "oauth_scope": self._configured_value(raw_drive.get("oauth_scope")),
                    "oauth_authorize_uri": self._configured_value(
                        raw_drive.get("oauth_authorize_uri")
                    ),
                    "api_base_uri": self._configured_value(
                        raw_drive.get("api_base_uri")
                    ),
                    "redirect_uri": redirect_uri,
                    "token_uri": self._configured_value(raw_drive.get("token_uri")),
                }
            except Exception:
                return empty_values

    def _read_profile_metadata(self) -> dict[str, dict[str, Any]]:
        """Handle read profile metadata."""
        config_path = Path(self.active_config)
        if not config_path.exists():
            return {}
        try:
            parsed = load_yaml(str(config_path), missing_ok=True)
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
                    metadata["google_auth_required"] = not auth_present
                    metadata["google_setup_present"] = bool(
                        client_id and client_secret and (folder_id or folder_url)
                    )
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
            if not requires_auth:
                return ""
            if not self.admin_ui_enabled:
                return "Enable admin UI to authorise"
            return f"<a class='btn' href='/admin/google-drive?profile={escape(name)}'>Authorise Google Drive</a>"

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

    def _profile_payload(self, *, name: str, profile: dict[str, Any]) -> dict[str, Any]:
        """Normalise a profile entry for API/UI responses."""
        storage = profile.get("storage") if isinstance(profile, dict) else {}
        scope = profile.get("scope") if isinstance(profile, dict) else {}
        auth = profile.get("auth") if isinstance(profile, dict) else {}
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
        return {
            "name": name,
            "backend": backend,
            "roots": roots,
            "api_keys_count": len(api_keys),
            "profile": profile,
        }

    def _list_profile_payloads(self) -> list[dict[str, Any]]:
        """Return all configured profiles from active config document."""
        document = self._load_config_document()
        profiles = document.get("profiles")
        if not isinstance(profiles, dict):
            return []
        payloads: list[dict[str, Any]] = []
        for name, profile in sorted(profiles.items()):
            if not isinstance(profile, dict):
                continue
            payloads.append(self._profile_payload(name=str(name), profile=profile))
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

    async def _handle_jobs_api(
        self,
        *,
        scope: dict[str, Any],
        headers: dict[str, str],
        path: str,
        send,
    ) -> bool:
        """Handle read-only jobs status API routes."""
        if scope.get("type") != "http":
            return False
        method = str(scope.get("method") or "").upper()
        if not (path == "/api/v1/jobs" or path.startswith("/api/v1/jobs/")):
            return False

        supplied_admin_token = headers.get("x-admin-token", "")
        ui_admin = bool(self.admin_ui_token and supplied_admin_token == self.admin_ui_token)
        auth_info, selected_profile = await self._authenticate_request(
            scope=scope, headers=headers
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
        if path == "/api/v1/jobs":
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
                    ),
                },
            )
            return True

        if path == "/api/v1/jobs/queue/status":
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
        if len(segments) == 4:
            job_id = segments[3]
            payload = runtime.get_job(job_id)
            if payload is None:
                await self._send_api_error(
                    send,
                    status=404,
                    code="NOT_FOUND",
                    message=f"Job not found: {job_id}",
                )
                return True
            await self._send_json(send, status=200, payload={"ok": True, "job": payload})
            return True

        await self._send_api_error(
            send,
            status=404,
            code="NOT_FOUND",
            message="Not Found",
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
        method = str(scope.get("method") or "").upper()
        accept = headers.get("accept", "")

        # Auth endpoints — handle before any other routing.
        if scope.get("type") == "http":
            if path == "/auth/login" and method == "POST":
                await self._handle_auth_login(receive, send, headers)
                return
            if path == "/auth/me" and method == "GET":
                await self._handle_auth_me(send, headers)
                return
            if path == "/auth/logout" and method == "POST":
                await self._handle_auth_logout(send, headers)
                return

        if scope.get("type") == "http" and method in {"GET", "HEAD"}:
            if path == "/runtime-config.js":
                await self._serve_runtime_config(send, method=method)
                return

            asset_path = self._resolve_ui_asset_path(path)
            if asset_path is not None:
                await self._send_file(send, path=asset_path, method=method)
                return

            if self._is_ui_route(path):
                await self._serve_spa_index(send, method=method)
                return

        health_paths = {self.health_path}
        ready_paths = {self._ready_path()}
        live_paths = {self._live_path()}
        if self.enable_legacy_api_alias:
            legacy_health = self._legacy_api_alias(self.health_path)
            legacy_ready = self._legacy_api_alias(self._ready_path())
            legacy_live = self._legacy_api_alias(self._live_path())
            legacy_root_health = self._legacy_root_alias(self.health_path)
            legacy_root_ready = self._legacy_root_alias(self._ready_path())
            legacy_root_live = self._legacy_root_alias(self._live_path())
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
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path in health_paths
        ):
            readiness, checks = self._dependency_checks()
            body = json.dumps(
                {
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
            ).encode("utf-8")
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
            payload = self._list_tools_payload()
            body = json.dumps(payload).encode("utf-8")
            await self._send_bytes(
                send, status=200, body=body, content_type="application/json"
            )
            return
        if (
            scope.get("type") == "http"
            and method == "GET"
            and path == self.a2a_health_path
        ):
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
        is_identity_api_route = (
            path == "/admin/users"
            or path.startswith("/admin/users/")
            or path == "/admin/groups"
            or path.startswith("/admin/groups/")
            or path == "/admin/api-keys"
            or path.startswith("/admin/api-keys/")
        )
        is_profile_api_alias_route = path == "/api/admin/profiles" or path.startswith(
            "/api/admin/profiles/"
        )
        profile_api_path = (
            path[len("/api") :] if is_profile_api_alias_route else path
        )
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
        if scope.get("type") == "http" and is_admin_route:
            if (
                is_webui_admin_route or path == "/admin/reload"
            ) and not self.admin_ui_enabled:
                await self._send_api_error(
                    send, status=404, code="NOT_FOUND", message="Not Found"
                )
                return
            if (is_webui_admin_route or path == "/admin/reload") and self.admin_ui_token:
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

        if scope.get("type") == "http" and (is_identity_api_route or is_profile_api_route):
            method = str(scope.get("method") or "GET").upper()
            supplied_admin_token = headers.get("x-admin-token", "")
            ui_admin = bool(
                self.admin_ui_token and supplied_admin_token == self.admin_ui_token
            )
            auth_info, selected_profile = await self._authenticate_request(
                scope=scope, headers=headers
            )
            scopes = self._token_scopes(auth_info)
            token_admin = self._has_admin_scope(scopes)
            is_authenticated = ui_admin or auth_info is not None
            if not is_authenticated:
                await self._send_api_error(
                    send,
                    status=401,
                    code="UNAUTHENTICATED",
                    message="Unauthorised",
                )
                return
            if method != "GET" and not (ui_admin or token_admin):
                await self._send_api_error(
                    send,
                    status=403,
                    code="FORBIDDEN",
                    message="Admin access required",
                )
                return

            try:
                segments = [segment for segment in profile_api_path.split("/") if segment]

                if is_profile_api_route:
                    if method == "GET" and len(segments) == 2:
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "profiles": self._list_profile_payloads()},
                        )
                        return

                    if method == "POST" and len(segments) == 2:
                        payload = await self._read_json_body(receive)
                        profile_name = str(payload.get("name") or "").strip()
                        if not profile_name:
                            raise AdminIdentityError(
                                "VALIDATION_ERROR", "profile name is required"
                            )
                        document = self._load_config_document()
                        profiles = document.setdefault("profiles", {})
                        if profile_name in profiles:
                            raise AdminIdentityError(
                                "CONFLICT",
                                f"profile already exists: {profile_name}",
                                status=409,
                            )
                        profile_body = payload.get("profile")
                        if isinstance(profile_body, dict):
                            profile = self._deep_copy_jsonish(profile_body)
                        else:
                            template = profiles.get(self.profile_name)
                            if not isinstance(template, dict) and profiles:
                                template = next(iter(profiles.values()))
                            if isinstance(template, dict):
                                profile = self._deep_copy_jsonish(template)
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
                        profiles[profile_name] = profile
                        self._write_config_document(document)
                        reload_result = None
                        if callable(self.reload_callback):
                            reload_result = self.reload_callback()
                        await self._send_json(
                            send,
                            status=201,
                            payload={
                                "ok": True,
                                "profile": self._profile_payload(
                                    name=profile_name,
                                    profile=profile,
                                ),
                                "reloaded": bool(reload_result),
                                "reload": reload_result,
                            },
                        )
                        return

                    if len(segments) == 3:
                        profile_name = segments[2]
                        document = self._load_config_document()
                        profiles = document.setdefault("profiles", {})
                        profile = profiles.get(profile_name)
                        if not isinstance(profile, dict):
                            raise AdminIdentityError(
                                "NOT_FOUND",
                                f"unknown profile: {profile_name}",
                                status=404,
                            )

                        if method == "GET":
                            await self._send_json(
                                send,
                                status=200,
                                payload={
                                    "ok": True,
                                    "profile": self._profile_payload(
                                        name=profile_name,
                                        profile=profile,
                                    ),
                                },
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
                            profiles[profile_name] = candidate
                            self._write_config_document(document)
                            reload_result = None
                            if callable(self.reload_callback):
                                reload_result = self.reload_callback()
                            await self._send_json(
                                send,
                                status=200,
                                payload={
                                    "ok": True,
                                    "profile": self._profile_payload(
                                        name=profile_name,
                                        profile=candidate,
                                    ),
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
                            del profiles[profile_name]
                            self._write_config_document(document)
                            reload_result = None
                            if callable(self.reload_callback):
                                reload_result = self.reload_callback()
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
                        created = service.create_user(
                            username=str(payload.get("username") or ""),
                            display_name=str(payload.get("display_name") or ""),
                            is_active=bool(payload.get("is_active", True)),
                            groups=payload.get("groups") or [],
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
                        updated = service.update_user(segments[2], data=payload)
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "user": updated},
                        )
                        return
                    if len(segments) == 3 and method == "DELETE":
                        deleted = service.delete_user(segments[2])
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
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "group": updated},
                        )
                        return
                    if len(segments) == 3 and method == "DELETE":
                        deleted = service.delete_group(segments[2])
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
                        await self._send_json(
                            send,
                            status=201,
                            payload={"ok": True, "api_key": created},
                        )
                        return
                    if len(segments) == 4 and segments[3] == "revoke" and method == "POST":
                        revoked = service.revoke_api_key(segments[2])
                        await self._send_json(
                            send,
                            status=200,
                            payload={"ok": True, "api_key": revoked},
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
                result = callback_fn(
                    state=state,
                    code=code,
                    config_path=Path(self.active_config),
                )
                reload_message = "Restart server to apply updated config."
                if self.admin_apply_on_callback and callable(self.reload_callback):
                    try:
                        reload_info = self.reload_callback()
                        reload_message = f"Config hot-reloaded for profile {reload_info.get('profile', self.profile_name)}."
                    except Exception as exc:
                        reload_message = f"Config written but hot-reload failed: {exc}"
                html = (
                    "<h1>Google Drive linked successfully</h1>"
                    f"<p>Profile: <b>{result.profile}</b></p>"
                    f"<p>Folder: <b>{result.folder_name}</b> ({result.folder_id})</p>"
                    f"<p>Config updated: <code>{result.config_path}</code></p>"
                    f'<p>Folder URL: <a href="{result.folder_url}">{result.folder_url}</a></p>'
                    f"<p>{escape(reload_message)}</p>"
                )
                self.logger.info(
                    "admin_google_drive_callback_success",
                    extra={
                        "profile": result.profile,
                        "folder_id": result.folder_id,
                        "config_path": result.config_path,
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
    suffix = Path(path).suffix.lower() if isinstance(path, str) else path.suffix.lower()
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
    return Path(cleaned)


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
                jobs_runtime.mark_failed(job_id, error=error_message)
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
            p = Path(resolved_path)
            if not p.exists():
                return None
            snapshot = create_snapshot(snapshot_dir, p)
        else:
            stat = backend.stat(resolved_path)
            if stat is None:
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
        entries = [
            entry.path for entry in backend.list_dir(resolved, recursive=recursive)
        ]
        return {"path": str(resolved), "entries": entries}

    def search_path_names(
        query: str,
        glob: str | None = None,
        regex: bool = False,
        max_results: int | None = None,
        max_file_mb: int | None = None,
        max_depth: int | None = None,
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
            roots = [Path(root).resolve() for root in profile.scope.roots]
            with enforce_timeout(effective_timeout):
                matches = search_paths(
                    query,
                    roots=roots,
                    glob=glob,
                    regex=regex,
                    max_file_mb=effective_max_mb,
                    max_depth=max_depth,
                )
            filtered: list[str] = []
            for path_obj in matches:
                try:
                    assert isinstance(policy, ScopePolicy)
                    policy.require(path_obj.resolve(), operation="read")
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
        from pathlib import PurePosixPath

        pattern = re.compile(query) if regex else None
        remote_roots: list[str] = [
            str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots
        ]

        def _depth_ok(root: str, candidate: str) -> bool:
            """Handle depth ok."""
            if max_depth is None:
                return True
            try:
                rel = PurePosixPath(candidate).relative_to(PurePosixPath(root))
            except Exception:
                return False
            return len(rel.parts) <= max_depth

        remote_filtered: list[str] = []
        timed_out = False
        started = time.monotonic()
        for candidate in backend.iter_paths(remote_roots, max_depth=max_depth):
            if effective_timeout is not None and effective_timeout > 0:
                if (time.monotonic() - started) >= effective_timeout:
                    timed_out = True
                    break
            if glob and not PurePosixPath(candidate).match(glob):
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
        regex: bool = False,
        max_results: int | None = None,
        encoding: str = "utf-8",
        max_file_mb: int | None = None,
        max_depth: int | None = None,
        timeout_s: int | None = None,
    ) -> Dict[str, Any]:
        """Search text content."""
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
            roots = [Path(root).resolve() for root in profile.scope.roots]
            with enforce_timeout(effective_timeout):
                matches = search_content(
                    query,
                    roots=roots,
                    glob=glob,
                    regex=regex,
                    encoding=encoding,
                    max_results=None,
                    max_file_mb=effective_max_mb,
                    max_depth=max_depth,
                )
            filtered_matches = []
            for match in matches:
                try:
                    assert isinstance(policy, ScopePolicy)
                    policy.require(match.path.resolve(), operation="read")
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
        from pathlib import PurePosixPath

        regex_pattern = re.compile(query) if regex else None
        remote_roots: list[str] = [
            str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots
        ]
        results: list[dict[str, Any]] = []

        def _depth_ok(root: str, candidate: str) -> bool:
            """Handle depth ok."""
            if max_depth is None:
                return True
            try:
                rel = PurePosixPath(candidate).relative_to(PurePosixPath(root))
            except Exception:
                return False
            return len(rel.parts) <= max_depth

        timed_out = False
        started = time.monotonic()
        for candidate in backend.iter_paths(remote_roots, max_depth=max_depth):
            if effective_timeout is not None and effective_timeout > 0:
                if (time.monotonic() - started) >= effective_timeout:
                    timed_out = True
                    break
            if glob and not PurePosixPath(candidate).match(glob):
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
                if Path(
                    resolved
                ).suffix.lower() not in text_like_exts or target_format not in {
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

            with enforce_timeout(effective_timeout):
                if simulate_delay_s and simulate_delay_s > 0:
                    time.sleep(simulate_delay_s)
                # Conversion backends operate on local filesystem paths. For remote storage,
                # stage the input into a temporary file and optionally upload the output.
                if storage_backend.backend_name == "local":
                    input_path = Path(resolved)
                    output_path_local = (
                        Path(resolved_output) if resolved_output else None
                    )
                    result = run_convert_file(
                        input_path,
                        target_format,
                        output_path=output_path_local,
                        max_input_mb=effective_max_mb,
                        timeout_s=None,
                        preferred_backend=backend if backend else None,
                    )
                else:
                    import tempfile

                    suffix = Path(resolved).suffix or ""
                    with tempfile.TemporaryDirectory() as td:
                        in_path = Path(td) / f"input{suffix}"
                        in_path.write_bytes(storage_backend.read_bytes(resolved))
                        out_path = Path(td) / f"output.{target_format}"
                        result = run_convert_file(
                            in_path,
                            target_format,
                            output_path=out_path,
                            max_input_mb=effective_max_mb,
                            timeout_s=None,
                            preferred_backend=backend if backend else None,
                        )
                        if resolved_output and result.output_path:
                            storage_backend.write_bytes(
                                resolved_output,
                                Path(result.output_path).read_bytes(),
                                overwrite=True,
                            )
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
            if Path(resolved).suffix.lower() in text_like_exts and target_format in {
                "txt",
                "md",
            }:
                if backend and backend != "builtin-text-copy":
                    return _done(_fail(str(exc), code="backend_unavailable"))
                content = storage_backend.read_bytes(resolved).decode(
                    "utf-8", errors="replace"
                )
                if resolved_output:
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
        ok, message = launch_meld(Path(resolved_a), Path(resolved_b))
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

        suffix = Path(resolved).suffix.lower()
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
        return {
            "ok": True,
            "user": admin_identity_service.create_user(
                username=username,
                display_name=display_name,
                is_active=is_active,
                groups=groups or [],
            ),
        }

    def admin_update_user(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update admin user."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "user": admin_identity_service.update_user(user_id, data=data)}

    def admin_delete_user(user_id: str) -> Dict[str, Any]:
        """Delete admin user."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "result": admin_identity_service.delete_user(user_id)}

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
        return {
            "ok": True,
            "group": admin_identity_service.create_group(
                name=name,
                description=description,
                roles=roles or [],
                is_active=is_active,
            ),
        }

    def admin_update_group(group_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update admin group."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "group": admin_identity_service.update_group(group_id, data=data)}

    def admin_delete_group(group_id: str) -> Dict[str, Any]:
        """Delete admin group."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "result": admin_identity_service.delete_group(group_id)}

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
        return {
            "ok": True,
            "api_key": admin_identity_service.create_api_key(
                user_id=user_id,
                label=label,
                scopes=scopes or [],
                profile_name=profile_name,
            ),
        }

    def admin_revoke_api_key(api_key_id: str) -> Dict[str, Any]:
        """Revoke admin API key."""
        _assert_admin_for_admin_tool()
        if admin_identity_service is None:
            raise RuntimeError("admin identity service unavailable")
        return {"ok": True, "api_key": admin_identity_service.revoke_api_key(api_key_id)}

    tools = ToolRegistry()
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="read_file", description="Read a text file"),
            handler=read_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(
                name="write_file",
                description="Write text to a file",
                mutating=True,
                supports_dry_run=True,
            ),
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
                description="Create a directory",
                mutating=True,
                supports_dry_run=True,
            ),
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
            meta=ToolMeta(name="list_dir", description="List directory entries"),
            handler=list_path,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="search_paths", description="Search file paths"),
            handler=search_path_names,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="search_content", description="Search file contents"),
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
                description="Validate file content by detected or explicit type",
                requires_validation=True,
            ),
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
                description="Convert file with limits and warning-based optional backend handling",
                mutating=False,
            ),
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
                description="Apply sed-like file edits with audit/snapshot support",
                mutating=True,
                requires_validation=True,
                supports_dry_run=True,
            ),
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


def register_tools_with_fastmcp(
    server: FastMCP,
    registry_provider,
    *,
    default_profile_name: str,
    logger: LogLike | None = None,
) -> None:
    """Execute register tools with fastmcp."""
    current_registry = registry_provider()

    def _extract_paths_from_params(params: Dict[str, Any]) -> Dict[str, str]:
        """Handle extract paths from params."""
        path_keys = ("path", "src", "dst", "path_a", "path_b")
        extracted: Dict[str, str] = {}
        for key in path_keys:
            value = params.get(key)
            if isinstance(value, str):
                extracted[key] = value
        return extracted

    def build_wrapped_handler(tool_name: str):
        """Build wrapped handler."""

        def wrapped_handler(*args, **kwargs):
            """Execute wrapped handler."""
            started = time.perf_counter()
            params = _truncate_value(kwargs)
            paths = _extract_paths_from_params(kwargs)
            profile_name = (
                get_request_profile_name(default_profile_name) or default_profile_name
            )
            registry = registry_provider()
            current_def = registry.get(tool_name)
            handler = current_def.handler
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
                result = handler(*args, **kwargs)
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

        setattr(wrapped_handler, "__signature__", inspect.signature(handler))
        wrapped_handler.__name__ = f"wrapped_{tool_name}"
        wrapped_handler.__doc__ = f"Dynamic wrapper for tool {tool_name}"
        wrapped_handler.__annotations__ = getattr(handler, "__annotations__", {})
        wrapped_handler.__module__ = getattr(handler, "__module__", __name__)
        return wrapped_handler

    for definition in current_registry.list_tools():
        handler = definition.handler
        tool_name = definition.meta.name
        wrapped_handler = build_wrapped_handler(tool_name)
        server.tool(name=definition.meta.name, description=definition.meta.description)(
            wrapped_handler
        )


def build_fastmcp_server(
    default_profile_name: str,
    config: ServerConfig,
    http: HttpRuntimeSettings,
    *,
    logger: LogLike | None = None,
    admin_identity_service: AdminIdentityService | None = None,
    jobs_runtime_factory: Callable[
        [ProfileConfig, str], FileMcpJobsRuntime | None
    ]
    | None = None,
) -> FastMCP:
    """Build fastmcp server."""
    if default_profile_name not in config.profiles:
        raise ValueError(f"Unknown default profile: {default_profile_name}")

    profile_auth = _build_profile_auth_map(config)
    for name, (resolved_keys, _, _) in profile_auth.items():
        if not resolved_keys:
            raise ValueError(f"No API keys configured for profile '{name}'")

    auth = MultiProfileApiKeyTokenVerifier(
        profile_auth,
        default_profile=default_profile_name,
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

    server = FastMCP(
        name=f"file-mcp-server:{default_profile_name}",
        auth=auth,
    )
    registry_lock = RLock()
    profiles_holder: dict[str, ProfileConfig] = dict(config.profiles)
    registry_by_profile: dict[str, ToolRegistry] = {}
    jobs_runtime_by_profile: dict[str, FileMcpJobsRuntime | None] = {}

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

    def _registry_provider() -> ToolRegistry:
        """Handle registry provider."""
        profile_name = (
            get_request_profile_name(default_profile_name) or default_profile_name
        )
        with registry_lock:
            registry = registry_by_profile.get(profile_name)
            if registry is None:
                profile = profiles_holder.get(profile_name)
                if profile is None:
                    profile = profiles_holder[default_profile_name]
                    profile_name = default_profile_name
                registry = build_tool_registry(
                    profile,
                    profile_name=profile_name,
                    logger=logger,
                    admin_identity_service=admin_identity_service,
                    jobs_runtime=_jobs_runtime_provider(profile_name),
                )
                registry_by_profile[profile_name] = registry
            return registry

    def _reload_registry(
        *, env_path: str | None, config_path: str | None, defaults_path: str | None
    ) -> dict[str, Any]:
        """Handle reload registry."""
        cfg = load_config(
            env_path=env_path, config_path=config_path, defaults_path=defaults_path
        )
        with registry_lock:
            for runtime in jobs_runtime_by_profile.values():
                if runtime is not None:
                    runtime.close()
            jobs_runtime_by_profile.clear()
            profiles_holder.clear()
            profiles_holder.update(cfg.profiles)
            registry_by_profile.clear()
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

    setattr(server, "_file_mcp_registry_provider", _registry_provider)
    setattr(server, "_file_mcp_reload_registry", _reload_registry)
    setattr(server, "_file_mcp_auth_verifier", auth)
    setattr(server, "_file_mcp_jobs_runtime_provider", _jobs_runtime_provider)
    setattr(server, "_file_mcp_jobs_runtime_close_all", _close_jobs_runtimes)

    register_tools_with_fastmcp(
        server,
        _registry_provider,
        default_profile_name=default_profile_name,
        logger=logger,
    )
    return server


async def run_fastmcp_http_server(
    *,
    default_profile_name: str,
    config: ServerConfig,
    http_config: HttpServerConfig,
    logger: LogLike | None = None,
) -> None:
    # Instantiate API-kit app config for PS-20 contract alignment and dependency verification.
    """Execute run fastmcp http server."""
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
    server = build_fastmcp_server(
        default_profile_name,
        config,
        http,
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

    endpoint_path = http.events_path if http.transport == "sse" else http.mcp_path
    middleware = [
        Middleware(RequestContextMiddleware),
        Middleware(
            StreamableHttpAcceptCompatibilityMiddleware,
            mcp_path=http.mcp_path,
        ),
        Middleware(
            HealthCheckMiddleware,
            health_path=http.health_path,
            profile_name=default_profile_name,
            transport=http.transport,
            reload_callback=_reload_callback,
            registry_provider=registry_provider,
            mcp_path=http.mcp_path,
            a2a_auth_verifier=auth_verifier,
            db_runtime=db_runtime,
            admin_identity_service=admin_identity_service,
            jobs_runtime_provider=jobs_runtime_provider,
            callback_host_fallback=http.host,
        ),
    ]
    if logger:
        logger.info(
            "Starting FastMCP",
            transport=http.transport,
            host=http.host,
            port=http.port,
            endpoint=endpoint_path,
            health=http.health_path,
        )

    try:
        await server.run_http_async(
            show_banner=False,
            transport=cast(Literal["http", "streamable-http", "sse"], http.transport),
            host=http.host,
            port=http.port,
            path=endpoint_path,
            middleware=middleware,
            stateless_http=http.stateless_http,
        )
    finally:
        if callable(jobs_runtime_close_all):
            jobs_runtime_close_all()
        shutdown_database()
