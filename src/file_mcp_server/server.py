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

import json
import logging
import sys
import time

from fastmcp import FastMCP
from file_tools.config.models import HttpServerConfig, ProfileConfig, ValidationConfig
from file_tools.audit import AuditLogger, build_event, create_snapshot, prune_snapshots
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
    copy_file,
    delete_file,
    list_dir,
    move_file,
    read_bytes,
    read_text,
    write_bytes,
    write_text,
)
from file_tools.scope import ScopePolicy
from file_tools.search import search_content, search_paths
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

    def __init__(self, app, *, health_path: str, profile_name: str, transport: str) -> None:
        self.app = app
        self.health_path = health_path
        self.profile_name = profile_name
        self.transport = transport

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == self.health_path
        ):
            body = json.dumps(
                {
                    "status": "ok",
                    "service": "file-mcp-server",
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
        await self.app(scope, receive, send)


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


def _resolve_path(policy: ScopePolicy, path: str, *, operation: str) -> Path:
    resolved = policy.normalize(path)
    policy.require(resolved, operation=operation)
    return resolved


def _validate_text(content_type: str, text: str, validation: ValidationConfig) -> Dict[str, Any]:
    result = validate_with_mode(content_type, text, validation)
    return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}


def _infer_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
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


def build_tool_registry(profile: ProfileConfig) -> ToolRegistry:
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )
    limits = profile.limits
    validation = profile.validation
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
                profile="default",
                paths=paths or {},
                details=details or {},
            )
        )

    def _snapshot_if_enabled(path: Path) -> Path | None:
        if not snapshots_enabled or not snapshot_dir or not path.exists():
            return None
        snapshot = create_snapshot(snapshot_dir, path)
        prune_snapshots(
            snapshot_dir,
            snapshot_retention_days,
            profile.snapshots.retention_count,
            profile.snapshots.max_storage_mb,
        )
        return snapshot

    def _resolve_path_for_tool(
        *,
        tool_name: str,
        action: str,
        path: str,
        operation: str,
        path_key: str = "path",
    ) -> Path:
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
        before = read_text(resolved, encoding=encoding)
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

        write_text(resolved, updated, encoding=encoding, overwrite=True)
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

        if start_byte is not None or end_byte is not None:
            data = read_bytes(resolved)
            start = 0 if start_byte is None else max(start_byte, 0)
            end = len(data) if end_byte is None else max(end_byte, 0)
            if end < start:
                raise ValueError("end_byte must be >= start_byte")
            return data[start:end].decode(encoding, errors="replace")

        text = read_text(resolved, encoding=encoding)
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
            write_text(resolved, content, encoding=encoding, overwrite=overwrite)
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
            delete_file(resolved, missing_ok=missing_ok)
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
            copy_file(resolved_src, resolved_dst, overwrite=overwrite)
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

    def move_path(src: str, dst: str, overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        resolved_src = _resolve_path_for_tool(
            tool_name="move_file",
            action="move",
            path=src,
            operation="move",
            path_key="src",
        )
        resolved_dst = _resolve_path_for_tool(
            tool_name="move_file",
            action="move",
            path=dst,
            operation="move",
            path_key="dst",
        )
        try:
            if dry_run:
                _write_audit(
                    tool_name="move_file",
                    action="move",
                    status="ok",
                    paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                    details={"dry_run": True},
                )
                return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": True}
            move_file(resolved_src, resolved_dst, overwrite=overwrite)
            _write_audit(
                tool_name="move_file",
                action="move",
                status="ok",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
                details={"dry_run": False},
            )
            return {"ok": True, "src": str(resolved_src), "dst": str(resolved_dst), "dry_run": False}
        except Exception:
            _write_audit(
                tool_name="move_file",
                action="move",
                status="error",
                paths={"src": str(resolved_src), "dst": str(resolved_dst)},
            )
            raise

    def list_path(path: str, recursive: bool = False) -> Dict[str, Any]:
        resolved = _resolve_path(policy, path, operation="read")
        entries = [str(item) for item in list_dir(resolved, recursive=recursive)]
        return {"path": str(resolved), "entries": entries}

    def search_path_names(
        query: str,
        glob: str | None = None,
        regex: bool = False,
        max_file_mb: int | None = None,
    ) -> Dict[str, Any]:
        roots = [Path(root).resolve() for root in profile.scope.roots]
        effective_max_mb = max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        matches = search_paths(
            query,
            roots=roots,
            glob=glob,
            regex=regex,
            max_file_mb=effective_max_mb,
        )
        filtered: list[str] = []
        for path in matches:
            try:
                policy.require(path.resolve(), operation="read")
                filtered.append(str(path))
            except Exception:
                continue
        return {"matches": filtered}

    def search_text_content(
        query: str,
        glob: str | None = None,
        regex: bool = False,
        max_results: int | None = None,
        encoding: str = "utf-8",
        max_file_mb: int | None = None,
    ) -> Dict[str, Any]:
        roots = [Path(root).resolve() for root in profile.scope.roots]
        effective_max_results = max_results if max_results is not None else limits.search_max_results
        effective_max_mb = max_file_mb if max_file_mb is not None else limits.search_max_file_mb
        matches = search_content(
            query,
            roots=roots,
            glob=glob,
            regex=regex,
            encoding=encoding,
            max_results=None,
            max_file_mb=effective_max_mb,
        )
        filtered_matches = []
        for match in matches:
            try:
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
        text = read_text(resolved, encoding=encoding)
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
        text = read_text(resolved, encoding=encoding)
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
                if resolved.suffix.lower() not in text_like_exts or target_format not in {"txt", "md"}:
                    return _fail("builtin-text-copy backend does not support input/target combination", code="unsupported_format")
                content = read_text(resolved, encoding="utf-8")
                if resolved_output:
                    write_text(resolved_output, content, encoding="utf-8", overwrite=True)
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
                result = run_convert_file(
                    resolved,
                    target_format,
                    output_path=resolved_output,
                    max_input_mb=effective_max_mb,
                    timeout_s=None,
                    preferred_backend=backend if backend else None,
                )
            payload: Dict[str, Any] = {
                "ok": True,
                "backend": result.backend or "auto",
                "used_fallback": False,
                "warnings": result.warnings,
            }
            if result.output_path:
                payload["output_path"] = str(result.output_path)
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
            if resolved.suffix.lower() in text_like_exts and target_format in {"txt", "md"}:
                if backend and backend != "builtin-text-copy":
                    return _fail(str(exc), code="backend_unavailable")
                content = read_text(resolved, encoding="utf-8")
                if resolved_output:
                    write_text(resolved_output, content, encoding="utf-8", overwrite=True)
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
        ok, message = launch_meld(resolved_a, resolved_b)
        return {
            "ok": ok,
            "path_a": str(resolved_a),
            "path_b": str(resolved_b),
            "warnings": [] if ok else [message],
            "message": message,
        }

    def b64_encode_file(path: str, urlsafe: bool = False) -> Dict[str, Any]:
        resolved = _resolve_path(policy, path, operation="read")
        data = read_bytes(resolved)
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
            write_bytes(resolved, decoded, overwrite=overwrite)
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
        text = read_text(resolved, encoding=encoding)
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
        return {
            "ok": True,
            "diff": diff_files(resolved_a, resolved_b, encoding=encoding, context=context),
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
        before = read_text(resolved, encoding=encoding)

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

        content_type = "markdown" if resolved.suffix.lower() == ".md" else "html" if resolved.suffix.lower() == ".html" else "json" if resolved.suffix.lower() == ".json" else ""
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
            write_text(resolved, updated, encoding=encoding, overwrite=True)
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
                name="move_file",
                description="Move a file",
                mutating=True,
                supports_dry_run=True,
            ),
            handler=move_path,
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
    return tools


def register_tools_with_fastmcp(server: FastMCP, registry: ToolRegistry) -> None:
    for definition in registry.list_tools():
        server.tool(name=definition.meta.name, description=definition.meta.description)(definition.handler)


def build_fastmcp_server(profile_name: str, profile: ProfileConfig, http: HttpRuntimeSettings) -> FastMCP:
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
    register_tools_with_fastmcp(server, build_tool_registry(profile))
    return server


async def run_fastmcp_http_server(
    *,
    profile_name: str,
    profile: ProfileConfig,
    http_config: HttpServerConfig,
    logger: logging.Logger | None = None,
) -> None:
    http = resolve_http_settings(http_config)
    server = build_fastmcp_server(profile_name, profile, http)
    endpoint_path = http.events_path if http.transport == "sse" else http.mcp_path
    middleware = [
        Middleware(
            HealthCheckMiddleware,
            health_path=http.health_path,
            profile_name=profile_name,
            transport=http.transport,
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
