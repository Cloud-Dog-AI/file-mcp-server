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

"""file-mcp-server — Route Guards Catalog (W28A-742).

License: Apache 2.0

The file-mcp-LOCAL method-aware route guard catalog. The central
``cloud_dog_idam.rbac.guard_registry`` is path-only (no method, no
resource_id_param); file-mcp's bespoke ASGI dispatch needs method-aware
+ resource-id-aware lookup, so this module owns the catalog. The shared
:func:`cloud_dog_idam.rbac.grants.authorise` is still the decision function
— this catalog only declares **which permission/resource_type/resource_id**
to ask about.

See the W28A-742 comparison map §3.2 + §3.4 for the full design rationale
and the verbatim raw-source anchors.

The catalog is exhaustive: every raw ``path == "..."`` / ``path.startswith("...")``
/ ``path in (...)`` branch under ``server_runtime.py::__call__`` falls into
exactly one of five buckets:

1. :data:`FILE_MCP_PUBLIC_ALLOWLIST` — anon-OK (built at app boot from
   ``health_paths`` / ``ready_paths`` / ``live_paths`` / ``status_paths`` sets;
   the default-config set is also enumerated here for static testing).
2. :data:`FILE_MCP_AUTH_PATHS` — anon-OK with materialisation semantics
   (login/me/logout/status).
3. :data:`FILE_MCP_UI_PATHS` — anon-OK SPA shell + assets + UI fallback.
4. :data:`FILE_MCP_IDAM_V1_PATTERN` — ``/idam/v1/*`` and ``/v1/idam/v1/*``
   (both forms route to the same DB-backed shim per
   ``server_runtime.py:3290`` substring check).
5. :data:`ROUTE_GUARDS` — every data/API/MCP/A2A/admin surface; each row
   declares ``(method, pattern, permission, resource_type,
   resource_id_extractor)``.

The :func:`classify` function returns the bucket name for any
``(method, path)`` pair; ``"unknown"`` means default-DENY (HARD FAIL in the
no-unguarded-route meta-test).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Literal, Mapping

# ───────────────────────── (1) PUBLIC ALLOWLIST ─────────────────────────

#: Default-config public-allowlist entries (anon-OK).
#:
#: At app boot, file-mcp's runtime builds ``health_paths``/``ready_paths``/
#: ``live_paths``/``status_paths`` sets (see ``server_runtime.py:3488-3492``)
#: that may include config-derived legacy aliases (``/app/v1/health``,
#: ``/api/v1/health``, etc.) when the operator configures legacy paths. The
#: SM1.2 meta-test enumerates those LIVE sets at runtime. This static set is
#: the default-config baseline used by unit tests + static analysis.
FILE_MCP_PUBLIC_ALLOWLIST: frozenset[str] = frozenset({
    "/health",
    "/ready",
    "/live",
    "/status",
    "/version",
    "/openapi.json",
    # Google OAuth redirect target. Google redirects the operator's browser here
    # cross-site, so the admin session cookie is NOT sent (SameSite) — requiring
    # admin auth on this route makes the callback fail with UNAUTHENTICATED, which is
    # exactly what blocked Drive setup. It is anon-OK because the callback handler
    # validates the OAuth ``state`` CSRF token (minted only by the admin-authed
    # /admin/google-drive/start), so the token exchange only proceeds for a pending state.
    "/admin/google-drive/callback",
})


# ───────────────────────── (2) AUTH PATHS ─────────────────────────

#: ``(method, path)`` tuples for auth endpoints. Anon-OK with materialisation
#: semantics: ``/auth/login`` may POST credentials and receive a cookie;
#: ``/auth/me`` / ``/auth/status`` return ``{user:null}``/``401`` for anon,
#: NEVER a default-admin principal (PS-82 §3.1 hard rule).
FILE_MCP_AUTH_PATHS: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/status"),
    ("GET", "/api/auth/status"),
})


# ───────────────────────── (3) UI PATHS ─────────────────────────

#: Static SPA shell paths (full match — anon-OK; the page renders a
#: login gate if the user is unauthenticated). See
#: ``server_runtime.py:1716-1732 _ui_route_paths`` + ``1763-1769
#: _is_ui_fallback_route``.
_FILE_MCP_UI_STATIC_PATHS: frozenset[str] = frozenset({
    "/",
    "/runtime-config.js",
    "/search",
    "/system/settings",
    "/system/about",
    "/file-browser",
    "/storage-profiles",
    "/profiles",
    "/source-connections",
    "/audit-log",
    "/developer/api-docs",
    "/developer/mcp-console",
    "/developer/a2a-console",
    "/system/jobs",
    "/google-drive-settings",
    "/admin/users",
    "/admin/groups",
    "/admin/roles",
    "/admin/rbac",
    "/admin/api-keys",
    "/login",
    "/logout",
})

#: SPA reserved prefixes that should NEVER fall through to the UI fallback
#: (these are API/MCP/A2A/admin surfaces — guarded explicitly). Mirrors
#: ``server_runtime.py:1740-1755`` reserved-prefixes tuple.
_UI_RESERVED_PREFIXES: tuple[str, ...] = (
    "/api",
    "/v1",
    "/auth",
    "/mcp",
    "/a2a",
    "/events",
    "/files",
    "/.well-known",
    "/health",
    "/status",
    "/openapi.json",
    "/ready",
    "/live",
    "/runtime-config.js",
    "/assets",
    "/admin/profiles",
    "/admin/google-drive",
)


def _is_ui_path(path: str, *, ui_base_path: str = "/ui") -> bool:
    """Return ``True`` for SPA shell + asset + fallback-route paths.

    Mirrors ``server_runtime.py`` ``_is_ui_route`` + ``_is_ui_fallback_route``
    behaviour so the catalog stays self-contained. The runtime is the source
    of truth at app boot; this helper is for static analysis.
    """
    if path in _FILE_MCP_UI_STATIC_PATHS:
        return True
    if path.startswith("/assets/") or path == "/assets":
        return True
    if ui_base_path and (
        path == ui_base_path or path.startswith(f"{ui_base_path}/")
    ):
        return True
    return False


# ───────────────────────── (4) IDAM-V1 PATHS ─────────────────────────

#: Pattern matching ``/idam/v1/*`` AND ``/v1/idam/v1/*``. Both forms hit the
#: substring-check shim at ``server_runtime.py:3290`` and the v3 §3.3
#: DB-backed handlers. ``/v1/idam/v1/...`` is the UI-side alias (line 3287
#: comment "the RBAC page calls /v1/idam/v1/<x>").
FILE_MCP_IDAM_V1_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/v1)/idam/v1/")


# ───────────────────────── (5) ROUTE GUARDS ─────────────────────────


@dataclass(frozen=True)
class RouteGuard:
    """One guarded-route declaration.

    The ASGI chokepoint in ``server_runtime.py::__call__`` calls
    :func:`match(method, path)` to retrieve the guard for the incoming
    request, then resolves the principal, then calls
    ``cloud_dog_idam.rbac.grants.authorise(...)`` with this guard's
    ``permission`` / ``resource_type`` / extracted ``resource_id``.

    A ``resource_id_extractor`` of ``None`` indicates the guard is a
    surface/feature gate (no per-resource scoping); ``authorise`` is called
    with ``resource_id=None``. A non-``None`` extractor receives the
    :class:`re.Match` object and the request args mapping (route handler
    fills it with header, query, and/or JSON body fields as appropriate)
    and returns the resource id (or ``None`` for LIST operations that use
    ``allowed_resource_ids`` instead).
    """

    method: str
    pattern: re.Pattern[str]
    permission: str
    resource_type: str | None = None
    resource_id_extractor: Callable[
        [re.Match[str], Mapping[str, object]], str | None
    ] | None = None
    admin_only: bool = False


def _extract_group(group_name: str) -> Callable[
    [re.Match[str], Mapping[str, object]], str | None
]:
    """Return an extractor that pulls ``group_name`` from the regex match."""

    def _extract(match: re.Match[str], args: Mapping[str, object]) -> str | None:
        try:
            return match.group(group_name)
        except (IndexError, KeyError):
            return None

    return _extract


def _extract_arg(arg_name: str) -> Callable[
    [re.Match[str], Mapping[str, object]], str | None
]:
    """Return an extractor that pulls ``arg_name`` from the request args."""

    def _extract(match: re.Match[str], args: Mapping[str, object]) -> str | None:
        value = args.get(arg_name)
        return None if value is None else str(value)

    return _extract


def _re(pattern: str) -> re.Pattern[str]:
    """Compile a route pattern with fullmatch anchoring."""
    return re.compile(pattern)


#: The route guard catalog. Every row is one entry from the v3 §3.4.4 table.
#: Ordering matters: ``match()`` returns the FIRST matching row, so more-
#: specific patterns come before less-specific ones (e.g. the per-resource
#: detail route before its list/collection root).
ROUTE_GUARDS: tuple[RouteGuard, ...] = (
    # Skill discovery and every MCP compatibility transport authenticate before
    # any package route can parse or dispatch a request.
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/a2a)?/\.well-known/agent\.json/?$"),
        permission="a2a.access",
    ),
    RouteGuard(
        method="*",
        pattern=_re(r"^/(?:mcp|messages|message|sse)/?$"),
        permission="mcp.access",
    ),
    # ── Row 1: F-741-1 fix — /a2a/health now requires auth ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/a2a/health/?$"),
        permission="a2a.access",
    ),
    # ── Row 2-4: MCP transport (JSON-RPC tools/list + tools/call) ──
    RouteGuard(
        method="POST",
        pattern=_re(r"^/mcp/?$"),
        permission="mcp.access",
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/webmcp/?$"),
        permission="mcp.access",
    ),
    # ── Row 5: A2A task dispatch ──
    RouteGuard(
        method="POST",
        pattern=_re(r"^/(?:a2a/)?tasks/?$"),
        permission="a2a.skills.execute",
        resource_type="a2a_skill",
        resource_id_extractor=_extract_arg("skill_id"),
    ),
    # ── Row 6-7: NEW per v2 sendback F2 — GET /mcp/tools + /webmcp/tools ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/mcp/tools/?$"),
        permission="mcp.access",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/webmcp/tools/?$"),
        permission="mcp.access",
    ),
    # ── Row 8-11: NEW per v2 sendback F4 — A2A events SSE + history ──
    # Both the canonical /a2a/events* paths AND the Traefik-stripped /events*
    # aliases hit the SAME router (mcp_api_kit_layer.py:447-462 dual-mount).
    RouteGuard(
        method="GET",
        pattern=_re(r"^/a2a/events/?$"),
        permission="a2a.access",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/a2a/events/history/?$"),
        permission="a2a.access",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/events/?$"),
        permission="a2a.access",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/events/history/?$"),
        permission="a2a.access",
    ),
    # ── Row 14-15: /api/v1/files — read/write ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/api/v1/files/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/api/v1/files/(?P<path>.+)$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/api/v1/files/(?P<path>.+)$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/api/v1/files/(?P<path>.+)$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/api/v1/files/(?P<path>.+)$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    # req: FR-012 FR-017
    # PS-78 canonical REST file lifecycle contract.
    RouteGuard(
        method="GET",
        pattern=_re(r"^/files/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/files/upload/?$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/files/upload_base64/?$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/files/(?P<file_id>[^/]+)/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/files/(?P<file_id>[^/]+)/download/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/files/(?P<file_id>[^/]+)/?$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    # ── Row 15a: /api/v1/profiles + /v1/profiles data aliases ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/profiles/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^(?:/api)?/v1/profiles/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^(?:/api)?/v1/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    RouteGuard(
        method="PATCH",
        pattern=_re(r"^(?:/api)?/v1/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^(?:/api)?/v1/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    # ── Row 15b: /v1/watches* storage change-watch (W28E-1870-B, PS-102 §5.5) ──
    # Read verbs (list/get/status/events) require files.read; lifecycle/mutating
    # verbs (create/ack/recover/pause/resume/test-event/delete) require
    # files.write — mirroring the storage read/write split. Scoped to the
    # storage_profile the watch is bound to. The inline handler
    # (server_runtime._handle_watches) enforces tenant/profile ownership on top.
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/watches/?$"),
        permission="files.read",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^(?:/api)?/v1/watches/?$"),
        permission="files.write",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/watches/(?P<watch_id>[^/]+)(?:/(?:status|events))?/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("watch_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^(?:/api)?/v1/watches/(?P<watch_id>[^/]+)/(?:ack|recover)/?$"),
        permission="files.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("watch_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^(?:/api)?/v1/watches/(?P<watch_id>[^/]+)/(?:pause|resume|test-event|test_event)/?$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("watch_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^(?:/api)?/v1/watches/(?P<watch_id>[^/]+)/?$"),
        permission="files.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("watch_id"),
    ),
    # ── Row 16-19: jobs ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/jobs/queue/status/?$"),
        permission="jobs.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/jobs/?$"),
        permission="jobs.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/jobs/(?P<job_id>[^/]+)/?$"),
        permission="jobs.read",
        resource_type="job",
        resource_id_extractor=_extract_group("job_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^(?:/api)?/v1/jobs/(?P<job_id>[^/]+)(?:/.*)?$"),
        permission="jobs.control",
        resource_type="job",
        resource_id_extractor=_extract_group("job_id"),
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^(?:/api)?/v1/jobs/(?P<job_id>[^/]+)(?:/.*)?$"),
        permission="jobs.control",
        resource_type="job",
        resource_id_extractor=_extract_group("job_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^(?:/api)?/v1/jobs/(?P<job_id>[^/]+)/?$"),
        permission="jobs.delete",
        resource_type="job",
        resource_id_extractor=_extract_group("job_id"),
        admin_only=True,
    ),
    # ── Row 20-21: logs ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/logs/?$"),
        permission="logs.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^(?:/api)?/v1/logs/(?P<event_id>[^/]+)/?$"),
        permission="logs.read",
        resource_type="audit_event",
        resource_id_extractor=_extract_group("event_id"),
    ),
    # ── Row 22-23: /admin/users ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/users/?$"),
        permission="idam.users.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/v1/users/?$"),
        permission="idam.users.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/users/(?P<user_id>[^/]+)/?$"),
        permission="idam.users.read",
        resource_type="user",
        resource_id_extractor=_extract_group("user_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/users/?$"),
        permission="idam.users.write",
        admin_only=True,
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/users/(?P<user_id>[^/]+)/?$"),
        permission="idam.users.write",
        resource_type="user",
        resource_id_extractor=_extract_group("user_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/users/(?P<user_id>[^/]+)/?$"),
        permission="idam.users.write",
        resource_type="user",
        resource_id_extractor=_extract_group("user_id"),
        admin_only=True,
    ),
    # ── Row 24-25: /admin/groups ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/groups/?$"),
        permission="idam.groups.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/v1/groups/?$"),
        permission="idam.groups.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/groups/(?P<group_id>[^/]+)/?$"),
        permission="idam.groups.read",
        resource_type="group",
        resource_id_extractor=_extract_group("group_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/groups/?$"),
        permission="idam.groups.write",
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/groups/(?P<group_id>[^/]+)(?:/.*)?$"),
        permission="idam.groups.write",
        resource_type="group",
        resource_id_extractor=_extract_group("group_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/groups/(?P<group_id>[^/]+)/members/?$"),
        permission="idam.groups.write",
        resource_type="group",
        resource_id_extractor=_extract_group("group_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/groups/(?P<group_id>[^/]+)/members/(?P<user_id>[^/]+)/?$"),
        permission="idam.groups.write",
        resource_type="group",
        resource_id_extractor=_extract_group("group_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/groups/(?P<group_id>[^/]+)/?$"),
        permission="idam.groups.write",
        resource_type="group",
        resource_id_extractor=_extract_group("group_id"),
        admin_only=True,
    ),
    # ── Row 26-27: /admin/api-keys ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/api-keys/?$"),
        permission="apikeys.read_own",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/v1/api-keys/?$"),
        permission="apikeys.read_own",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/api-keys/(?P<key_id>[^/]+)/?$"),
        permission="apikeys.read_own",
        resource_type="api_key",
        resource_id_extractor=_extract_group("key_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/api-keys/?$"),
        permission="apikeys.manage_own",
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/api-keys/(?P<key_id>[^/]+)/?$"),
        permission="apikeys.manage_own",
        resource_type="api_key",
        resource_id_extractor=_extract_group("key_id"),
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/api-keys/(?P<key_id>[^/]+)/?$"),
        permission="apikeys.manage_own",
        resource_type="api_key",
        resource_id_extractor=_extract_group("key_id"),
    ),
    # ── Row 28-29: /admin/roles ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/roles/?$"),
        permission="idam.roles.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/roles/(?P<role_id>[^/]+)/?$"),
        permission="idam.roles.read",
        resource_type="role",
        resource_id_extractor=_extract_group("role_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/roles/?$"),
        permission="idam.roles.write",
        admin_only=True,
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/roles/(?P<role_id>[^/]+)/?$"),
        permission="idam.roles.write",
        resource_type="role",
        resource_id_extractor=_extract_group("role_id"),
        admin_only=True,
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/roles/(?P<role_id>[^/]+)/?$"),
        permission="idam.roles.write",
        resource_type="role",
        resource_id_extractor=_extract_group("role_id"),
        admin_only=True,
    ),
    # ── Row 30-31: /admin/profiles (CFG-13: admin-only writes) ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/profiles/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/profiles/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        admin_only=True,
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
        admin_only=True,
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
        admin_only=True,
    ),
    # ── Row 32-33: /api/admin/profiles alias (server_runtime.py:3627) ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/api/admin/profiles/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/api/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.read",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/api/admin/profiles/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        admin_only=True,
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/api/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
        admin_only=True,
    ),
    RouteGuard(
        method="DELETE",
        pattern=_re(r"^/api/admin/profiles/(?P<profile_id>[^/]+)/?$"),
        permission="profiles.write",
        resource_type="storage_profile",
        resource_id_extractor=_extract_group("profile_id"),
        admin_only=True,
    ),
    # ── Row 34: /admin/identity ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/identity/?$"),
        permission="idam.users.read",
    ),
    # ── Row 35: /admin/google-drive* ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/google-drive/?$"),
        permission="files.gdrive.read",
        resource_type="google_drive_profile",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/google-drive/(?P<rest>.+)$"),
        permission="files.gdrive.read",
        resource_type="google_drive_profile",
        resource_id_extractor=_extract_arg("profile"),
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/google-drive/start/?$"),
        permission="files.gdrive.write",
        resource_type="google_drive_profile",
        admin_only=True,
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/google-drive/callback/?$"),
        permission="files.gdrive.write",
        resource_type="google_drive_profile",
        admin_only=True,
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/google-drive/callback/?$"),
        permission="files.gdrive.write",
        resource_type="google_drive_profile",
        admin_only=True,
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/google-drive/(?P<action>[^/]+)/?$"),
        permission="files.gdrive.write",
        resource_type="google_drive_profile",
        admin_only=True,
    ),
    # ── Row 36: /admin/reload ──
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/reload/?$"),
        permission="config.write",
        admin_only=True,
    ),
    # ── Row 37: /admin/runtime-config ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/runtime-config/?$"),
        permission="config.read",
    ),
    RouteGuard(
        method="POST",
        pattern=_re(r"^/admin/runtime-config/?$"),
        permission="config.write",
        admin_only=True,
    ),
    RouteGuard(
        method="PUT",
        pattern=_re(r"^/admin/runtime-config/?$"),
        permission="config.write",
        admin_only=True,
    ),
    # ── Row 38: /admin/rbac (UI alias → /idam/v1/rbac/bindings) ──
    RouteGuard(
        method="GET",
        pattern=_re(r"^/admin/rbac/?$"),
        permission="idam.rbac.read",
    ),
    # ── Row 39-40: /v1/admin/* + /api/* — generic proxy fallbacks.
    # These are catch-alls for paths that proxy down to the FastAPI/MCP
    # sub-apps. The guard fires on the canonical /admin/* path resolved
    # by the proxy; this row exists so the meta-test does not flag the
    # proxy-prefix branches as "unknown". Required permission is the
    # weakest the proxy guarantees — admin actions still get gated
    # downstream.
    RouteGuard(
        method="GET",
        pattern=_re(r"^/v1/admin/?$"),
        permission="idam.users.read",
    ),
    RouteGuard(
        method="GET",
        pattern=_re(r"^/v1/admin/.+$"),
        permission="idam.users.read",
    ),
)


# ───────────────────────── PUBLIC API ─────────────────────────


def match(method: str, path: str) -> tuple[RouteGuard, re.Match[str]] | None:
    """Return the first :class:`RouteGuard` that matches ``(method, path)``.

    Returns ``None`` when no guard matches — the caller (the ASGI chokepoint)
    should treat that as default-DENY for any path that is not in one of the
    anon-OK buckets.
    """
    for guard in ROUTE_GUARDS:
        if guard.method != method and guard.method != "*":
            continue
        m = guard.pattern.match(path)
        if m is None:
            continue
        return guard, m
    return None


_Bucket = Literal["public", "auth", "ui", "idam_v1", "guarded", "unknown"]


def classify(method: str, path: str, *, ui_base_path: str = "/ui") -> _Bucket:
    """Classify ``(method, path)`` into one of the five buckets, else ``"unknown"``.

    Order matters: API/data paths that ALSO happen to render an SPA shell on
    GET+``Accept: text/html`` (e.g. ``/admin/users``) MUST classify as
    ``"guarded"`` first — the ASGI chokepoint handles the HTML short-circuit
    separately by inspecting the Accept header before invoking the guard.

    Order:

    1. ``public`` — :data:`FILE_MCP_PUBLIC_ALLOWLIST` (anon-OK).
    2. ``auth`` — :data:`FILE_MCP_AUTH_PATHS` (anon-OK with materialisation).
    3. ``guarded`` — matched by :func:`match` (one of :data:`ROUTE_GUARDS`).
    4. ``idam_v1`` — :data:`FILE_MCP_IDAM_V1_PATTERN` (guarded inline in
       ``server_runtime.py`` IDAM shim per §3.3).
    5. ``ui`` — SPA shell / asset / fallback (anon-OK; last because
       ``_is_ui_path`` is a permissive heuristic).
    6. else ``unknown`` — HARD FAIL in the meta-test (default-DENY at runtime).
    """
    if path in FILE_MCP_PUBLIC_ALLOWLIST:
        return "public"
    if (method, path) in FILE_MCP_AUTH_PATHS:
        return "auth"
    if match(method, path) is not None:
        return "guarded"
    if FILE_MCP_IDAM_V1_PATTERN.search(path):
        return "idam_v1"
    if _is_ui_path(path, ui_base_path=ui_base_path):
        return "ui"
    return "unknown"


def all_registered_keys() -> set[tuple[str, str]]:
    """Return ``{(method, pattern_str)}`` for every row in :data:`ROUTE_GUARDS`.

    Used by the SM1.2 no-unguarded-route meta-test to enumerate the catalog
    + intersect it with the live MCP tool registry + A2A skill registry +
    raw AST scan of ``server_runtime.py::__call__``.
    """
    return {(guard.method, guard.pattern.pattern) for guard in ROUTE_GUARDS}


__all__ = [
    "FILE_MCP_PUBLIC_ALLOWLIST",
    "FILE_MCP_AUTH_PATHS",
    "FILE_MCP_IDAM_V1_PATTERN",
    "ROUTE_GUARDS",
    "RouteGuard",
    "match",
    "classify",
    "all_registered_keys",
]
