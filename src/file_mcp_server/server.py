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
from pathlib import Path
from typing import Any, Dict, Optional, TextIO
from threading import Lock
from html import escape

import contextvars
import inspect
import json
import logging
import os
import sys
import time
import uuid
from urllib.parse import parse_qs

from fastmcp import FastMCP
from file_tools.config.models import HttpServerConfig, ProfileConfig, ValidationConfig
from file_tools.config.loader import get_profile, load_config
from file_tools.audit import AuditLogger, build_event, create_snapshot, create_snapshot_bytes, prune_snapshots
from file_tools.diff import diff_files, diff_text, launch_meld
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
    chmod_path,
    copy_file,
    create_dir,
    delete_file,
    list_dir,
    move_path as io_move_path,
    read_bytes,
    read_text,
    rename_path,
    write_bytes,
    write_text,
)
from file_tools.scope import ScopePolicy, PosixScopePolicy
from file_tools.search import search_content, search_paths
from file_tools.storage import NotSupportedError, StorageBackend, build_storage_backend
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
from starlette.middleware import Middleware

from .auth import ApiKeyTokenVerifier
from .endpoint_health import ENDPOINT_HEALTH_MANAGER
from .google_drive_admin import (
    begin_oauth,
    complete_oauth_callback,
    parse_form_urlencoded,
    render_setup_page,
)


@dataclass(frozen=True)
class JsonRpcError:
    code: int
    message: str


@dataclass(frozen=True)
class HttpRuntimeSettings:
    transport: str
    host: str
    port: int
    mcp_path: str
    health_path: str
    events_path: str
    stateless_http: bool


def _build_response(request_id: Any, result: Any = None, error: JsonRpcError | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": error.code, "message": error.message}
    else:
        payload["result"] = result
    return payload


class DispatchError(RuntimeError):
    """Raised when a request cannot be dispatched."""


class StdioServer:
    """Legacy stdio transport for compatibility with existing tests."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def handle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if not method:
            return _build_response(request_id, error=JsonRpcError(-32600, "Missing method"))

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

    def serve(self, *, input_stream: Optional[TextIO] = None, output_stream: Optional[TextIO] = None) -> None:
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

    def __init__(self, app, *, health_path: str, profile_name: str, transport: str, reload_callback=None) -> None:
        self.app = app
        self.health_path = health_path
        self.profile_name = profile_name
        self.transport = transport
        self.reload_callback = reload_callback
        self.app_name = "file-mcp-server"
        self.env_file = str(os.getenv("FILE_MCP_ACTIVE_ENV_PATH") or "") or None
        self.active_config = str(os.getenv("FILE_MCP_ACTIVE_CONFIG_PATH") or "config.yaml")
        self.profile_names = [
            name.strip()
            for name in (os.getenv("FILE_MCP_ACTIVE_PROFILE_NAMES") or profile_name).split(",")
            if name.strip()
        ]
        self.admin_ui_enabled = _to_bool(os.getenv("FILE_MCP_ADMIN_UI_ENABLED"), default=False)
        self.admin_ui_token = str(os.getenv("FILE_MCP_ADMIN_UI_TOKEN") or "").strip()
        self.admin_apply_on_callback = _to_bool(os.getenv("FILE_MCP_ADMIN_APPLY_ON_CALLBACK"), default=True)

    async def _read_http_body(self, receive) -> bytes:
        body = b""
        while True:
            event = await receive()
            if event.get("type") != "http.request":
                continue
            body += event.get("body", b"")
            if not event.get("more_body", False):
                break
        return body

    async def _send_bytes(self, send, *, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
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
        await self._send_bytes(send, status=status, body=html.encode("utf-8"), content_type="text/html; charset=utf-8")

    async def _send_redirect(self, send, *, location: str) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 302,
                "headers": [(b"location", location.encode("utf-8"))],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def __call__(self, scope, receive, send) -> None:
        headers = {
            (k.decode("latin-1").lower() if isinstance(k, bytes) else str(k).lower()): (
                v.decode("latin-1") if isinstance(v, bytes) else str(v)
            )
            for k, v in (scope.get("headers") or [])
        }
        path = str(scope.get("path") or "")
        is_admin_route = path.startswith("/admin/")
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == self.health_path
        ):
            body = json.dumps(
                {
                    "status": "ok",
                    "service": "file-mcp-server",
                    "application": {"name": self.app_name},
                    "runtime": {"env_file": self.env_file},
                    "profile": self.profile_name,
                    "transport": self.transport,
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
        if scope.get("type") == "http" and is_admin_route:
            if not self.admin_ui_enabled:
                await self._send_bytes(send, status=404, body=b"Not Found")
                return
            if self.admin_ui_token:
                query = parse_qs(scope.get("query_string", b"").decode("utf-8"), keep_blank_values=True)
                provided = (query.get("token") or [""])[0]
                if not provided:
                    provided = headers.get("x-admin-token", "")
                if provided != self.admin_ui_token:
                    await self._send_bytes(send, status=401, body=b"Unauthorized")
                    return

        if scope.get("type") == "http" and scope.get("method") == "GET" and scope.get("path") == "/admin/google-drive":
            scheme = scope.get("scheme") or "http"
            host = headers.get("host", "localhost")
            callback_url = f"{scheme}://{host}/admin/google-drive/callback"
            html = render_setup_page(
                callback_url=callback_url,
                profiles=self.profile_names or [self.profile_name],
                status_message="",
            )
            await self._send_html(send, status=200, html=html)
            return
        if scope.get("type") == "http" and scope.get("method") == "POST" and scope.get("path") == "/admin/google-drive/start":
            body = await self._read_http_body(receive)
            try:
                data = parse_form_urlencoded(body)
                location = begin_oauth(data)
                await self._send_redirect(send, location=location)
                return
            except Exception as exc:
                html = render_setup_page(
                    callback_url="",
                    profiles=self.profile_names or [self.profile_name],
                    status_message=f"Failed to start OAuth flow: {exc}",
                    status_type="warn",
                )
                await self._send_html(send, status=400, html=html)
                return
        if scope.get("type") == "http" and scope.get("method") == "GET" and scope.get("path") == "/admin/google-drive/callback":
            query = parse_qs(scope.get("query_string", b"").decode("utf-8"), keep_blank_values=True)
            state = (query.get("state") or [""])[0]
            code = (query.get("code") or [""])[0]
            if not state or not code:
                await self._send_html(send, status=400, html="<h1>Missing state or code in callback.</h1>")
                return
            try:
                result = complete_oauth_callback(
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
                    f"<p>Folder URL: <a href=\"{result.folder_url}\">{result.folder_url}</a></p>"
                    f"<p>{escape(reload_message)}</p>"
                )
                await self._send_html(send, status=200, html=html)
                return
            except Exception as exc:
                await self._send_html(send, status=400, html=f"<h1>OAuth callback failed</h1><pre>{exc}</pre>")
                return
        if scope.get("type") == "http" and scope.get("method") == "POST" and scope.get("path") == "/admin/reload":
            if not callable(self.reload_callback):
                await self._send_bytes(send, status=501, body=b"Reload callback not configured")
                return
            try:
                result = self.reload_callback()
                body = json.dumps({"ok": True, "result": result}).encode("utf-8")
                await self._send_bytes(send, status=200, body=body, content_type="application/json")
                return
            except Exception as exc:
                body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                await self._send_bytes(send, status=500, body=body, content_type="application/json")
                return
        await self.app(scope, receive, send)


_request_client_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "file_mcp_request_client_ip", default=None
)
_request_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "file_mcp_request_session_id", default=None
)


class RequestContextMiddleware:
    """Capture request context for per-tool operational logging."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        client = scope.get("client") or ()
        client_ip = client[0] if isinstance(client, tuple) and client else None
        headers = {
            (key.decode("latin-1").lower() if isinstance(key, bytes) else str(key).lower()):
            (value.decode("latin-1") if isinstance(value, bytes) else str(value))
            for key, value in (scope.get("headers") or [])
        }
        if headers.get("x-forwarded-for"):
            client_ip = headers["x-forwarded-for"].split(",")[0].strip()
        session_id = (
            headers.get("x-session-id")
            or headers.get("x-request-id")
            or str(uuid.uuid4())
        )

        ip_token = _request_client_ip.set(client_ip)
        sid_token = _request_session_id.set(session_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _request_client_ip.reset(ip_token)
            _request_session_id.reset(sid_token)


def _to_bool(value: Any, default: bool) -> bool:
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
    base = _normalize_path(base_path, default="/")
    sub = _normalize_path(path, default="/")
    if base == "/":
        return sub
    if sub == "/":
        return base
    return f"{base}{sub}"


def resolve_http_settings(http_config: HttpServerConfig) -> HttpRuntimeSettings:
    transport = (http_config.transport or "streamable-http").strip().lower()
    if transport not in {"streamable-http", "sse", "http"}:
        transport = "streamable-http"

    base_path = _normalize_path(http_config.base_path, default="/")
    mcp_path = _join_paths(base_path, _normalize_path(http_config.mcp_path, default="/mcp"))
    health_path = _join_paths(base_path, _normalize_path(http_config.health_path, default="/health"))
    events_path = _join_paths(base_path, _normalize_path(http_config.events_path, default="/events"))

    return HttpRuntimeSettings(
        transport=transport,
        host=(http_config.host or "127.0.0.1").strip(),
        port=_to_int(http_config.port, default=8000),
        mcp_path=mcp_path,
        health_path=health_path,
        events_path=events_path,
        stateless_http=_to_bool(http_config.stateless_http, default=False),
    )


def _resolve_path(policy: ScopePolicy | PosixScopePolicy, path: str, *, operation: str) -> str:
    if isinstance(policy, ScopePolicy):
        resolved = policy.normalize(path)
        policy.require(resolved, operation=operation)
        return str(resolved)
    resolved_posix = policy.normalize(path)
    policy.require(str(resolved_posix), operation=operation)
    return str(resolved_posix)


def _validate_text(content_type: str, text: str, validation: ValidationConfig) -> Dict[str, Any]:
    result = validate_with_mode(content_type, text, validation)
    return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}


def _infer_content_type(path: str | Path) -> str:
    suffix = (Path(path).suffix.lower() if isinstance(path, str) else path.suffix.lower())
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
    logger: logging.Logger | None = None,
) -> ToolRegistry:
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
    snapshots_enabled = bool(profile.snapshots.enabled and snapshot_dir and profile.snapshots.mode != "none")
    snapshot_retention_days = profile.snapshots.retention_days

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
        if not audit_logger:
            return
        audit_logger.write(
            build_event(
                tool=tool_name,
                action=action,
                status=status,
                outcome=outcome or status,
                profile=profile_name,
                session_id=_request_session_id.get(),
                client_ip=_request_client_ip.get(),
                duration_ms=duration_ms,
                params=params or {},
                paths=paths or {},
                details=details or {},
            )
        )

    def _snapshot_if_enabled(resolved_path: str) -> Path | None:
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
        return _backend_health_snapshot()

    def read_file(
        path: str,
        encoding: str = "utf-8",
        start_line: int | None = None,
        end_line: int | None = None,
        start_byte: int | None = None,
        end_byte: int | None = None,
    ) -> str:
        resolved = _resolve_path(policy, path, operation="read")
        if (start_line is not None or end_line is not None) and (start_byte is not None or end_byte is not None):
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
                    details={"dry_run": True, "snapshot_path": str(snapshot) if snapshot else None},
                )
                return {"ok": True, "path": str(resolved), "dry_run": True}
            backend.write_bytes(resolved, content.encode(encoding), overwrite=overwrite)
            _write_audit(
                tool_name="write_file",
                action="write",
                status="ok",
                paths={"path": str(resolved)},
                details={"dry_run": False, "snapshot_path": str(snapshot) if snapshot else None},
            )
            return {"ok": True, "path": str(resolved), "dry_run": False}
        except Exception:
            _write_audit(tool_name="write_file", action="write", status="error", paths={"path": str(resolved)})
            raise

    def delete_path(path: str, missing_ok: bool = False, dry_run: bool = False) -> Dict[str, Any]:
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
                    details={"dry_run": True, "snapshot_path": str(snapshot) if snapshot else None},
                )
                return {"ok": True, "path": str(resolved), "dry_run": True}
            backend.delete_path(resolved, missing_ok=missing_ok)
            _write_audit(
                tool_name="delete_file",
                action="delete",
                status="ok",
                paths={"path": str(resolved)},
                details={"dry_run": False, "snapshot_path": str(snapshot) if snapshot else None},
            )
            return {"ok": True, "path": str(resolved), "dry_run": False}
        except Exception:
            _write_audit(tool_name="delete_file", action="delete", status="error", paths={"path": str(resolved)})
            raise

    def copy_path(src: str, dst: str, overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
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
                return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": True}
            backend.copy_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name="copy_file",
                action="copy",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": False}
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
            _write_audit(tool_name="create_dir", action="mkdir", status="error", paths={"path": str(resolved)})
            raise

    def _parse_octal_mode(mode: int | str) -> int:
        if isinstance(mode, int):
            return mode
        if isinstance(mode, str):
            normalized = mode.strip().lower()
            if normalized.startswith("0o"):
                return int(normalized, 8)
            return int(normalized, 8)
        raise ValueError("mode must be an int or octal string")

    def chmod_fs_path(path: str, mode: int | str, recursive: bool = False, dry_run: bool = False) -> Dict[str, Any]:
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
                    details={"dry_run": True, "mode": oct(parsed_mode), "recursive": recursive},
                )
                return {"ok": True, "path": str(resolved), "mode": oct(parsed_mode), "dry_run": True}
            backend.chmod_path(resolved, parsed_mode, recursive=recursive)
            _write_audit(
                tool_name="chmod_path",
                action="chmod",
                status="ok",
                paths={"path": str(resolved)},
                details={"dry_run": False, "mode": oct(parsed_mode), "recursive": recursive},
            )
            return {"ok": True, "path": str(resolved), "mode": oct(parsed_mode), "dry_run": False}
        except Exception:
            _write_audit(tool_name="chmod_path", action="chmod", status="error", paths={"path": str(resolved)})
            raise

    def move_path_handler(
        src: str,
        dst: str,
        overwrite: bool = False,
        dry_run: bool = False,
        *,
        tool_name: str = "move_file",
    ) -> Dict[str, Any]:
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
                return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": True}
            backend.move_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name=tool_name,
                action="move",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name=tool_name,
                action="move",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def rename_path_handler(src: str, dst: str, overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
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
                return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": True}
            backend.rename_path(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name="rename_path",
                action="rename",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="rename_path",
                action="rename",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def list_path(path: str, recursive: bool = False) -> Dict[str, Any]:
        resolved = _resolve_path(policy, path, operation="read")
        entries = [entry.path for entry in backend.list_dir(resolved, recursive=recursive)]
        return {"path": str(resolved), "entries": entries}

    def search_path_names(
        query: str,
        glob: str | None = None,
        regex: bool = False,
        max_file_mb: int | None = None,
        max_depth: int | None = None,
        timeout_s: int | None = None,
    ) -> Dict[str, Any]:
        effective_max_mb = max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        effective_timeout = timeout_s if timeout_s is not None else limits.search_timeout_s

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
                except Exception:
                    continue
            return {"matches": filtered}

        import re
        from pathlib import PurePosixPath

        pattern = re.compile(query) if regex else None
        roots = [str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots]  # type: ignore[arg-type]

        def _depth_ok(root: str, candidate: str) -> bool:
            if max_depth is None:
                return True
            try:
                rel = PurePosixPath(candidate).relative_to(PurePosixPath(root))
            except Exception:
                return False
            return len(rel.parts) <= max_depth

        filtered: list[str] = []
        with enforce_timeout(effective_timeout):
            for candidate in backend.iter_paths(roots, max_depth=max_depth):
                if glob and not PurePosixPath(candidate).match(glob):
                    continue
                if not any(_depth_ok(root, candidate) for root in roots):
                    continue
                try:
                    if effective_max_mb is not None:
                        stat = backend.stat(candidate)
                        if stat is not None and stat.size is not None and stat.size > effective_max_mb * 1024 * 1024:
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
                filtered.append(candidate)
        return {"matches": filtered}

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
        effective_max_results = max_results if max_results is not None else limits.search_max_results
        effective_max_mb = max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        effective_timeout = timeout_s if timeout_s is not None else limits.search_timeout_s

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
                    if effective_max_results is not None and len(filtered_matches) >= effective_max_results:
                        break
                except Exception:
                    continue
            return {
                "matches": [
                    {"path": str(match.path), "line_no": match.line_no, "line": match.line}
                    for match in filtered_matches
                ]
            }

        import re
        from pathlib import PurePosixPath

        pattern = re.compile(query) if regex else None
        roots = [str(PosixScopePolicy.normalize(root)) for root in profile.scope.roots]  # type: ignore[arg-type]
        results: list[dict[str, Any]] = []

        def _depth_ok(root: str, candidate: str) -> bool:
            if max_depth is None:
                return True
            try:
                rel = PurePosixPath(candidate).relative_to(PurePosixPath(root))
            except Exception:
                return False
            return len(rel.parts) <= max_depth

        with enforce_timeout(effective_timeout):
            for candidate in backend.iter_paths(roots, max_depth=max_depth):
                if glob and not PurePosixPath(candidate).match(glob):
                    continue
                if not any(_depth_ok(root, candidate) for root in roots):
                    continue
                try:
                    assert isinstance(policy, PosixScopePolicy)
                    policy.require(candidate, operation="read")
                except Exception:
                    continue
                try:
                    if effective_max_mb is not None:
                        stat = backend.stat(candidate)
                        if stat is not None and stat.size is not None and stat.size > effective_max_mb * 1024 * 1024:
                            continue
                except Exception:
                    continue
                try:
                    text = backend.read_bytes(candidate).decode(encoding, errors="replace")
                except Exception:
                    continue
                for line_no, line in enumerate(text.splitlines(), start=1):
                    ok = pattern.search(line) is not None if regex else (query in line)
                    if ok:
                        results.append({"path": candidate, "line_no": line_no, "line": line})
                        if effective_max_results is not None and len(results) >= effective_max_results:
                            return {"matches": results}
        return {"matches": results}

    def json_set_file(
        path: str,
        json_path: str,
        value: Any,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
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
        return _mutating_edit_file(
            tool_name="yaml_delete_file",
            path=path,
            operation="write",
            content_type="yaml",
            transform=lambda text: yaml_delete(text, yaml_path),
            encoding=encoding,
            dry_run=dry_run,
        )

    def json_get_file(path: str, json_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
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
        return _mutating_edit_file(
            tool_name="json_merge_file",
            path=path,
            operation="write",
            content_type="json",
            transform=lambda text: json_merge(text, json_path, value),
            encoding=encoding,
            dry_run=dry_run,
        )

    def yaml_get_file(path: str, yaml_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
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
        resolved = _resolve_path(policy, path, operation="read")
        resolved_output = _resolve_path(policy, output_path, operation="write") if output_path else None
        effective_max_mb = max_input_mb if max_input_mb is not None else profile.conversion.max_input_mb
        effective_timeout = timeout_s if timeout_s is not None else limits.conversion_timeout_s

        def _fail(message: str, *, backend: str | None = None, code: str = "conversion_error") -> Dict[str, Any]:
            return {
                "ok": False,
                "backend": backend,
                "used_fallback": False,
                "error_code": code,
                "warnings": [message],
            }

        try:
            if backend == "builtin-text-copy":
                text_like_exts = {".txt", ".md", ".json", ".yaml", ".yml", ".html", ".xml"}
                if Path(resolved).suffix.lower() not in text_like_exts or target_format not in {"txt", "md"}:
                    return _fail("builtin-text-copy backend does not support input/target combination", code="unsupported_format")
                content = storage_backend.read_bytes(resolved).decode("utf-8", errors="replace")
                if resolved_output:
                    storage_backend.write_bytes(resolved_output, content.encode("utf-8"), overwrite=True)
                    return {
                        "ok": True,
                        "backend": "builtin-text-copy",
                        "used_fallback": False,
                        "warnings": [],
                        "output_path": str(resolved_output),
                    }
                return {
                    "ok": True,
                    "backend": "builtin-text-copy",
                    "used_fallback": False,
                    "warnings": [],
                    "content": content,
                }

            with enforce_timeout(effective_timeout):
                if simulate_delay_s and simulate_delay_s > 0:
                    time.sleep(simulate_delay_s)
                # Conversion backends operate on local filesystem paths. For remote storage,
                # stage the input into a temporary file and optionally upload the output.
                if storage_backend.backend_name == "local":
                    input_path = Path(resolved)
                    output_path_local = Path(resolved_output) if resolved_output else None
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
                                resolved_output, Path(result.output_path).read_bytes(), overwrite=True
                            )
            payload: Dict[str, Any] = {
                "ok": True,
                "backend": result.backend or "auto",
                "used_fallback": False,
                "warnings": result.warnings,
            }
            if result.output_path:
                payload["output_path"] = str(resolved_output) if resolved_output else str(result.output_path)
            if result.content is not None:
                payload["content"] = result.content
            return payload
        except BackendNotFoundError as exc:
            return _fail(str(exc), backend=backend, code="unknown_backend")
        except BackendUnavailableError as exc:
            return _fail(str(exc), backend=backend, code="backend_unavailable")
        except BackendCannotHandleError as exc:
            return _fail(str(exc), backend=backend, code="unsupported_format")
        except ConversionError as exc:
            # Deterministic built-in fallback for text-like sources when external backends are unavailable.
            text_like_exts = {".txt", ".md", ".json", ".yaml", ".yml", ".html", ".xml"}
            if Path(resolved).suffix.lower() in text_like_exts and target_format in {"txt", "md"}:
                if backend and backend != "builtin-text-copy":
                    return _fail(str(exc), code="backend_unavailable")
                content = storage_backend.read_bytes(resolved).decode("utf-8", errors="replace")
                if resolved_output:
                    storage_backend.write_bytes(resolved_output, content.encode("utf-8"), overwrite=True)
                    return {
                        "ok": True,
                        "backend": "builtin-text-copy",
                        "used_fallback": True,
                        "warnings": ["fallback_text_copy"],
                        "output_path": str(resolved_output),
                    }
                return {
                    "ok": True,
                    "backend": "builtin-text-copy",
                    "used_fallback": True,
                    "warnings": ["fallback_text_copy"],
                    "content": content,
                }
            return _fail(str(exc), code="backend_unavailable")
        except TimeoutError as exc:
            return _fail(str(exc), code="timeout")
        except LimitError as exc:
            return _fail(str(exc), code="limit_exceeded")

    def meld_files_tool(path_a: str, path_b: str) -> Dict[str, Any]:
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
        resolved = _resolve_path_for_tool(
            tool_name="b64_decode_to_file",
            action="write",
            path=path,
            operation="write",
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
                return {"ok": True, "path": str(resolved), "dry_run": True, "bytes_written": len(decoded)}
            backend.write_bytes(resolved, decoded, overwrite=overwrite)
            _write_audit(
                tool_name="b64_decode_to_file",
                action="write",
                status="ok",
                paths={"path": str(resolved)},
                details={"snapshot_path": str(snapshot) if snapshot else None, "dry_run": False},
            )
            return {"ok": True, "path": str(resolved), "bytes_written": len(decoded), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="b64_decode_to_file",
                action="write",
                status="error",
                paths={"path": str(resolved)},
            )
            raise

    def validate_file(path: str, content_type: str | None = None, encoding: str = "utf-8") -> Dict[str, Any]:
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

    def diff_files_tool(path_a: str, path_b: str, encoding: str = "utf-8", context: int = 3) -> Dict[str, Any]:
        resolved_a = _resolve_path(policy, path_a, operation="read")
        resolved_b = _resolve_path(policy, path_b, operation="read")
        a_text = backend.read_bytes(resolved_a).decode(encoding, errors="replace")
        b_text = backend.read_bytes(resolved_b).decode(encoding, errors="replace")
        return {
            "ok": True,
            "diff": diff_text(a_text, b_text, context=context, fromfile=str(resolved_a), tofile=str(resolved_b)),
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
        resolved = _resolve_path_for_tool(
            tool_name="sed_edit_file",
            action="edit_text",
            path=path,
            operation="edit",
        )
        snapshot = _snapshot_if_enabled(resolved)
        before = backend.read_bytes(resolved).decode(encoding, errors="replace")

        def _apply_single(current: str, op_args: Dict[str, Any]) -> str:
            single_op = op_args.get("op")
            if single_op == "replace_regex":
                single_pattern = op_args.get("pattern")
                single_repl = op_args.get("repl")
                single_count = int(op_args.get("count", 0))
                if single_pattern is None or single_repl is None:
                    raise ValueError("pattern and repl are required for replace_regex")
                return replace_regex(current, single_pattern, single_repl, count=single_count).text
            if single_op == "insert_before_line":
                single_line_no = op_args.get("line_no")
                single_content = op_args.get("content")
                if single_line_no is None or single_content is None:
                    raise ValueError("line_no and content are required for insert_before_line")
                return insert_before_line(current, int(single_line_no), str(single_content)).text
            if single_op == "insert_after_line":
                single_line_no = op_args.get("line_no")
                single_content = op_args.get("content")
                if single_line_no is None or single_content is None:
                    raise ValueError("line_no and content are required for insert_after_line")
                return insert_after_line(current, int(single_line_no), str(single_content)).text
            if single_op == "delete_matching_lines":
                single_pattern = op_args.get("pattern")
                if single_pattern is None:
                    raise ValueError("pattern is required for delete_matching_lines")
                return delete_matching_lines(current, str(single_pattern)).text
            if single_op == "replace_line_range":
                single_start = op_args.get("start")
                single_end = op_args.get("end")
                if single_start is None or single_end is None:
                    raise ValueError("start and end are required for replace_line_range")
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
                return {"ok": True, "path": str(resolved), "warnings": warnings, "dry_run": True}
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
            return {"ok": True, "path": str(resolved), "warnings": warnings, "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="sed_edit_file",
                action="edit_text",
                status="error",
                paths={"path": str(resolved)},
                details={"op": operation_label},
            )
            raise

    tools = ToolRegistry()
    tools.register(ToolDefinition(meta=ToolMeta(name="read_file", description="Read a text file"), handler=read_file))
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
        ToolDefinition(meta=ToolMeta(name="list_dir", description="List directory entries"), handler=list_path)
    )
    tools.register(
        ToolDefinition(meta=ToolMeta(name="search_paths", description="Search file paths"), handler=search_path_names)
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="search_content", description="Search file contents"),
            handler=search_text_content,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="diff_text", description="Generate unified diff for text"),
            handler=lambda before, after, context=3: diff_text(before, after, context=context),
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
            meta=ToolMeta(name="b64_encode_file", description="Encode file contents as base64"),
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
            handler=lambda content_type, text: _validate_text(content_type, text, validation),
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
            meta=ToolMeta(name="json_set", description="Set JSON value by path", mutating=True),
            handler=lambda text, path, value: json_set(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="json_delete", description="Delete JSON value by path", mutating=True),
            handler=lambda text, path: json_delete(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="json_copy", description="Copy JSON value by path", mutating=True),
            handler=lambda text, from_path, to_path: json_copy(text, from_path, to_path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="json_move", description="Move JSON value by path", mutating=True),
            handler=lambda text, from_path, to_path: json_move(text, from_path, to_path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="json_merge", description="Merge JSON value by path", mutating=True),
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
            meta=ToolMeta(name="yaml_set", description="Set YAML value by path", mutating=True),
            handler=lambda text, path, value: yaml_set(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_delete", description="Delete YAML value by path", mutating=True),
            handler=lambda text, path: yaml_delete(text, path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_copy", description="Copy YAML value by path", mutating=True),
            handler=lambda text, from_path, to_path: yaml_copy(text, from_path, to_path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_move", description="Move YAML value by path", mutating=True),
            handler=lambda text, from_path, to_path: yaml_move(text, from_path, to_path),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_merge", description="Merge YAML value by path", mutating=True),
            handler=lambda text, path, value: yaml_merge(text, path, value),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="markdown_get_section", description="Extract markdown section"),
            handler=lambda text, heading: md_get_section(text, heading),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="markdown_set_section", description="Replace markdown section", mutating=True),
            handler=lambda text, heading, new_content: md_set_section(text, heading, new_content),
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="replace_regex", description="Apply regex replacement", mutating=True),
            handler=lambda text, pattern, repl, count=0: replace_regex(
                text, pattern, repl, count=count
            ).text,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="diff_files", description="Generate unified diff for files"),
            handler=diff_files_tool,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="meld_files", description="Launch meld for file comparison (optional integration)"),
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
            meta=ToolMeta(name="json_get_file", description="Get JSON value from file by path"),
            handler=json_get_file,
        )
    )
    tools.register(
        ToolDefinition(
            meta=ToolMeta(name="yaml_get_file", description="Get YAML value from file by path"),
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
    setattr(tools, "profile_config", profile)
    setattr(tools, "profile_name", profile_name)
    setattr(tools, "storage_backend_name", active_backend)
    setattr(tools, "endpoint_health_manager", ENDPOINT_HEALTH_MANAGER)
    setattr(tools, "logger", logger)
    setattr(tools, "audit_writer", _write_audit)
    return tools


def _truncate_value(value: Any) -> Any:
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
    profile_name: str,
    logger: logging.Logger | None = None,
) -> None:
    current_registry = registry_provider()

    def _extract_paths_from_params(params: Dict[str, Any]) -> Dict[str, str]:
        path_keys = ("path", "src", "dst", "path_a", "path_b")
        extracted: Dict[str, str] = {}
        for key in path_keys:
            value = params.get(key)
            if isinstance(value, str):
                extracted[key] = value
        return extracted

    def build_wrapped_handler(tool_name: str):
        def wrapped_handler(*args, **kwargs):
            started = time.perf_counter()
            params = _truncate_value(kwargs)
            paths = _extract_paths_from_params(kwargs)
            registry = registry_provider()
            current_def = registry.get(tool_name)
            handler = current_def.handler
            audit_writer = getattr(registry, "audit_writer", None)
            endpoint_health_manager = getattr(registry, "endpoint_health_manager", None)
            storage_backend_name = getattr(registry, "storage_backend_name", None)
            profile_config = getattr(registry, "profile_config", None)
            restart_on_threshold = (
                _to_bool(getattr(profile_config.endpoint_health, "restart_on_threshold", None), default=False)
                if profile_config is not None
                else False
            )
            restart_exit_code = (
                _to_int(getattr(profile_config.endpoint_health, "restart_exit_code", None), default=75)
                if profile_config is not None
                else 75
            )
            if (
                endpoint_health_manager is not None
                and storage_backend_name
                and profile_config is not None
                and tool_name != "backend_status"
            ):
                state = endpoint_health_manager.get_state(profile_name, storage_backend_name)
                if state is not None and state.status != "healthy":
                    state = endpoint_health_manager.maybe_recover_backend(
                        profile_name=profile_name,
                        profile=profile_config,
                        backend_name=storage_backend_name,
                        logger=logger,
                    ) or state
                    if state.status != "healthy":
                        message = (
                            f"Backend unavailable: backend={storage_backend_name} "
                            f"status={state.status} reason={state.reason} "
                            f"requires_restart={state.requires_restart}"
                        )
                        if logger:
                            logger.warning(message)
                        if state.requires_restart and restart_on_threshold:
                            if logger:
                                logger.error(
                                    "Endpoint restart threshold reached for backend=%s; exiting process with code=%s",
                                    storage_backend_name,
                                    restart_exit_code,
                                )
                            raise SystemExit(restart_exit_code)
                        raise RuntimeError(message)
            if logger:
                logger.info(
                    json.dumps(
                        {
                            "event": "tool_call",
                            "profile": profile_name,
                            "tool": tool_name,
                            "params": params,
                            "session_id": _request_session_id.get(),
                            "client_ip": _request_client_ip.get(),
                        },
                        ensure_ascii=False,
                    )
                )
            try:
                result = handler(*args, **kwargs)
                elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
                if logger:
                    logger.info(
                        json.dumps(
                            {
                                "event": "tool_result",
                                "profile": profile_name,
                                "tool": tool_name,
                                "outcome": "ok",
                                "duration_ms": elapsed_ms,
                                "session_id": _request_session_id.get(),
                                "client_ip": _request_client_ip.get(),
                            },
                            ensure_ascii=False,
                        )
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
                        json.dumps(
                            {
                                "event": "tool_result",
                                "profile": profile_name,
                                "tool": tool_name,
                                "outcome": "error",
                                "error": str(exc),
                                "duration_ms": elapsed_ms,
                                "session_id": _request_session_id.get(),
                                "client_ip": _request_client_ip.get(),
                            },
                            ensure_ascii=False,
                        )
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

        wrapped_handler.__signature__ = inspect.signature(handler)
        wrapped_handler.__name__ = f"wrapped_{tool_name}"
        wrapped_handler.__doc__ = f"Dynamic wrapper for tool {tool_name}"
        wrapped_handler.__annotations__ = getattr(handler, "__annotations__", {})
        wrapped_handler.__module__ = getattr(handler, "__module__", __name__)
        return wrapped_handler

    for definition in current_registry.list_tools():
        handler = definition.handler
        tool_name = definition.meta.name
        wrapped_handler = build_wrapped_handler(tool_name)
        server.tool(name=definition.meta.name, description=definition.meta.description)(wrapped_handler)


def build_fastmcp_server(
    profile_name: str,
    profile: ProfileConfig,
    http: HttpRuntimeSettings,
    *,
    logger: logging.Logger | None = None,
) -> FastMCP:
    if not profile.auth.api_keys:
        raise ValueError("No API keys configured for selected profile")

    auth = ApiKeyTokenVerifier(
        profile.auth.api_keys,
        header_name=profile.auth.header_name,
        header_scheme=profile.auth.header_scheme,
    )

    server = FastMCP(
        name=f"file-mcp-server:{profile_name}",
        auth=auth,
    )
    registry_lock = Lock()
    registry_holder: dict[str, ToolRegistry] = {
        "registry": build_tool_registry(profile, profile_name=profile_name, logger=logger)
    }

    def _registry_provider() -> ToolRegistry:
        with registry_lock:
            return registry_holder["registry"]

    def _reload_registry(*, env_path: str | None, config_path: str | None, defaults_path: str | None) -> dict[str, Any]:
        cfg = load_config(env_path=env_path, config_path=config_path, defaults_path=defaults_path)
        next_profile = get_profile(cfg, name=profile_name)
        with registry_lock:
            registry_holder["registry"] = build_tool_registry(next_profile, profile_name=profile_name, logger=logger)
        ENDPOINT_HEALTH_MANAGER.run_startup_checks(profile_name=profile_name, profile=next_profile, logger=logger)
        states = ENDPOINT_HEALTH_MANAGER.get_profile_states(profile_name)
        return {
            "profile": profile_name,
            "reloaded": True,
            "endpoint_health": {name: state.__dict__.copy() for name, state in states.items()},
        }

    setattr(server, "_file_mcp_registry_provider", _registry_provider)
    setattr(server, "_file_mcp_reload_registry", _reload_registry)

    register_tools_with_fastmcp(
        server,
        _registry_provider,
        profile_name=profile_name,
        logger=logger,
    )
    return server


async def run_fastmcp_http_server(
    *,
    profile_name: str,
    profile: ProfileConfig,
    http_config: HttpServerConfig,
    logger: logging.Logger | None = None,
) -> None:
    http = resolve_http_settings(http_config)
    ENDPOINT_HEALTH_MANAGER.run_startup_checks(profile_name=profile_name, profile=profile, logger=logger)
    if _to_bool(profile.endpoint_health.restart_on_threshold, default=False):
        exit_code = _to_int(profile.endpoint_health.restart_exit_code, default=75)
        states = ENDPOINT_HEALTH_MANAGER.get_profile_states(profile_name)
        for state in states.values():
            if state.requires_restart:
                if logger:
                    logger.error(
                        "Endpoint startup health exceeded restart threshold for backend=%s; exiting with code=%s",
                        state.backend,
                        exit_code,
                    )
                raise SystemExit(exit_code)
    server = build_fastmcp_server(profile_name, profile, http, logger=logger)
    reload_fn = getattr(server, "_file_mcp_reload_registry", None)
    env_path = os.getenv("FILE_MCP_ACTIVE_ENV_PATH") or None
    config_path = os.getenv("FILE_MCP_ACTIVE_CONFIG_PATH") or None
    defaults_path = os.getenv("FILE_MCP_ACTIVE_DEFAULTS_PATH") or None

    def _reload_callback():
        if not callable(reload_fn):
            raise RuntimeError("reload function unavailable")
        return reload_fn(env_path=env_path, config_path=config_path, defaults_path=defaults_path)

    endpoint_path = http.events_path if http.transport == "sse" else http.mcp_path
    middleware = [
        Middleware(RequestContextMiddleware),
        Middleware(
            HealthCheckMiddleware,
            health_path=http.health_path,
            profile_name=profile_name,
            transport=http.transport,
            reload_callback=_reload_callback,
        )
    ]
    if logger:
        logger.info(
            "Starting FastMCP transport=%s host=%s port=%s endpoint=%s health=%s",
            http.transport,
            http.host,
            http.port,
            endpoint_path,
            http.health_path,
        )

    await server.run_http_async(
        show_banner=False,
        transport=http.transport,
        host=http.host,
        port=http.port,
        path=endpoint_path,
        middleware=middleware,
        stateless_http=http.stateless_http,
    )
