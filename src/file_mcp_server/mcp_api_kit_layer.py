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

"""MCP transport via cloud_dog_api_kit for file-mcp-server tool dispatch."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, Request

from cloud_dog_api_kit.errors import UnauthenticatedError, UnauthorisedError
from cloud_dog_api_kit.errors.handler import register_error_handlers
from cloud_dog_api_kit.mcp import ToolContract, register_mcp_routes
from cloud_dog_api_kit.mcp.contract import register_mcp_contract  # PS-50 MCP contract
from cloud_dog_idam.rbac import RBACEngine  # PS-50 per-tool RBAC
try:
    from cloud_dog_api_kit.mcp.tool_audit import mcp_tool_audit_middleware
except ImportError:
    from .mcp_tool_audit_shim import mcp_tool_audit_middleware

from file_tools.tools.registry import ToolRegistry

from .auth import MultiProfileApiKeyTokenVerifier

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
        inner = profile_tool_factory(tool_name)
        return inner(**kwargs)

    audited = mcp_tool_audit_middleware(
        tool_name,
        _sync_core,
        service="file-mcp-server",
        redact_fields=_EXTRA_AUDIT_REDACT,
    )

    async def _handler(payload: dict[str, Any], request: Request) -> Any:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise UnauthenticatedError("Authentication required for MCP tool calls")
        token = getattr(user, "access_token", None)
        scopes = list(getattr(token, "scopes", None) or [])
        if not _scopes_allow(required, scopes):
            raise UnauthorisedError(f"Missing permission: {required}")
        return audited(**payload)

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
        out[name] = ToolContract(
            name=name,
            handler=handler,
            description=definition.meta.description,
            input_schema={},
            output_schema={},
        )
    return out


def build_mcp_fastapi_application(
    registry_provider: Callable[[], ToolRegistry],
    auth_verifier: MultiProfileApiKeyTokenVerifier,
    *,
    profile_tool_factory: Callable[[str], Callable[..., Any]],
) -> FastAPI:
    """FastAPI ASGI app: MCP JSON-RPC + api_kit transport + IDAM middleware."""
    seed = registry_provider()
    contracts = build_tool_contracts(
        registry_provider,
        auth_verifier,
        seed_registry=seed,
        profile_tool_factory=profile_tool_factory,
    )
    app = FastAPI(title="file-mcp-server-mcp", version="1.0.0", docs_url=None, redoc_url=None)
    register_error_handlers(app)
    for mw in auth_verifier.get_middleware():
        app.add_middleware(mw.cls, *mw.args, **mw.kwargs)
    # PS-50: register_mcp_contract for standard tool catalogue + transport.
    register_mcp_contract(app, contracts, transport_modes=["streamable_http", "http_jsonrpc", "legacy_sse"])
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
