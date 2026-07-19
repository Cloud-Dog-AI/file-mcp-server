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

"""file-mcp-server — ASGI route-guard chokepoint (W28A-742).

License: Apache 2.0

The chokepoint inserted near the top of
``HealthCheckMiddleware.__call__``. For each incoming HTTP request it
classifies ``(method, path)`` against :mod:`file_mcp_server.route_guards`
(five anon-OK buckets or ``guarded``/``unknown``) and:

1. For ``"public"`` / ``"auth"`` / ``"ui"`` / ``"idam_v1"`` paths: returns
   ``False`` — the caller falls through to the existing dispatch.
2. For ``"guarded"`` paths:
     - If the request carries **no credentials at all** (no
       ``Authorization`` header, no ``X-API-Key`` header, no
       session cookie) the chokepoint returns **401**. This is the
       F-741-1 closure — PS-82 FR1.46 says ``GET /a2a/health`` without
       valid auth SHALL return 401, and the same principle applies to
       every guarded route. The previous file-mcp behaviour silently
       returned 200 for some routes without credentials; the chokepoint
       prevents that bypass class structurally.
     - If credentials are present, the chokepoint defers to the existing
       dispatch (cookie middleware + ``MultiProfileApiKeyTokenVerifier``
       + per-tool / per-route RBAC) to verify them and decide. This
       avoids duplicating verification logic and keeps the per-route
       RBAC intact. A syntactically malformed ``Authorization`` header is
       not counted as a credential carrier; otherwise some A2A health/event
       routes can treat "auth header present" as sufficient and return 200.
3. For ``"unknown"`` paths: returns ``False`` (fall through). The SM1.2
   meta-test is the structural catalogue-coverage gate; a runtime
   ``"unknown"`` for a path the meta-test missed would simply receive the
   existing dispatch's existing behaviour.

The resource-level binding cascade (W28A-741 keystone) is enforced INLINE
inside the ``/idam/v1/rbac/bindings`` handlers in ``server_runtime.py``,
which open their own DB session per request and call
``cloud_dog_idam.rbac.grants.authorise`` directly.

See the W28A-742 comparison map §3.1 + the v2 sendback for the full
rationale.
"""

from __future__ import annotations

import json
from hmac import compare_digest
from typing import Any

from . import route_guards


def _denied_body(code: str, message: str) -> bytes:
    """Build a file-mcp-shape error envelope per UT1.1 contract.

    Mirrors the existing file-mcp ``mcp_api_kit_layer.py`` error envelope
    so test fixtures that assert on ``body["errors"]`` (list with
    ``code`` + ``message``) and ``body["meta"]["correlation_id"]``
    (uuid) continue to work and the WebUI's error renderer handles the
    response uniformly.
    """
    import uuid as _uuid
    return json.dumps(
        {
            "ok": False,
            "errors": [{"code": code, "message": message}],
            "meta": {"correlation_id": str(_uuid.uuid4())},
        }
    ).encode("utf-8")


async def _send_status(send: Any, status: int, body: bytes) -> None:
    """Send a JSON response with the given status."""
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


# req: FR-017
def _request_carries_credentials(
    runtime: Any, headers: dict[str, str]
) -> bool:
    """Return ``True`` when the request carries ANY credential.

    The chokepoint defers verification + permission resolution to the
    existing dispatch when credentials are present. This is purely a
    presence check — invalid credentials are still rejected by the
    downstream verifier, but the F-741-1 anon-401 gate fires only when
    no credentials at all are presented.

    Recognised credential carriers:
      - syntactically usable ``Authorization`` header (Bearer / Token / Basic)
      - ``X-API-Key`` header (file-mcp dynamic API keys)
      - ``X-Admin-Token`` header (file-mcp admin-reload custom header
        per ``server_runtime.py`` ``FILE_MCP_ADMIN_UI_TOKEN``)
      - session cookie (file-mcp ``file_web_session`` default)
    """
    raw_authorization = (headers.get("authorization") or "").strip()
    if raw_authorization:
        parts = raw_authorization.split(None, 1)
        if (
            len(parts) == 2
            and parts[0].lower() in {"bearer", "token", "basic"}
            and parts[1].strip()
        ):
            return True
    if headers.get("x-api-key"):
        return True
    if headers.get("x-admin-token"):
        return True

    cookie_header = headers.get("cookie", "")
    if not cookie_header:
        return False
    cookie_name = getattr(runtime, "_cookie_name", "file_web_session")
    if not cookie_name:
        cookie_name = "file_web_session"
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{cookie_name}="):
            return True
    return False


def _is_html_fallback(headers: dict[str, str], path: str, *, ui_base_path: str) -> bool:
    """Return ``True`` when the request looks like an SPA HTML navigation.

    File-mcp's bespoke ASGI serves SOME ``/admin/*`` paths in two modes
    based on the ``Accept`` header: ``text/html`` returns the SPA shell
    (anon-OK; the SPA itself renders the login gate if the user is not
    authenticated) and ``application/json`` returns the API JSON (auth
    required). The chokepoint must respect this dual-mode dispatch so
    browser navigation to ``/admin/users`` (HTML) does not 401 from the
    F-741-1 closure intended only for the API surface.

    Mirrors the file-mcp ``_is_ui_fallback_route`` heuristic without
    requiring the ``/api``/``/v1``/etc. reserved-prefix check (those
    paths are already classified as ``ui`` by ``route_guards.classify``
    via :func:`route_guards._is_ui_path` when applicable). For an
    explicitly ``guarded``-classified path, we ADDITIONALLY allow HTML
    fallback ONLY when the path is NOT under one of the strict API-only
    prefixes (``/api``, ``/v1``, ``/mcp``, ``/webmcp``, ``/a2a``,
    ``/events``, ``/webapi``, ``/weba2a``, ``/admin/reload``).
    """
    accept = headers.get("accept", "") or ""
    if "text/html" not in accept.lower():
        return False
    # Hard-API-only prefixes — never serve HTML SPA for these.
    api_only_prefixes = (
        "/api",
        "/v1",
        "/mcp",
        "/webmcp",
        "/a2a",
        "/events",
        "/webapi",
        "/weba2a",
        "/admin/reload",
        "/admin/google-drive/callback",
    )
    for prefix in api_only_prefixes:
        if path == prefix or path.startswith(f"{prefix}/"):
            return False
    # Static assets are not HTML SPA either.
    if path.startswith("/assets/") or path == "/assets":
        return False
    # File-extension paths are also not SPA fallback.
    last_segment = path.rsplit("/", 1)[-1]
    if "." in last_segment:
        return False
    return True


# Backwards-compat shims used by `server_runtime.py::_w28a742_handle_rbac_bindings`
# to share the same principal-resolution semantics with the inline handlers.
# These remain on the helper API for the handler code paths even though the
# chokepoint itself no longer calls them directly.
def _resolve_principal_lightweight(
    runtime: Any, scope: Any, headers: dict[str, str]
) -> dict[str, Any] | None:
    """Resolve a principal from cookie OR API key for the inline handlers.

    Returns ``None`` for anonymous. The function performs the *same*
    presence checks the chokepoint uses (cookie session + API-key
    header), but for the inline handlers we also need the user_id +
    role to authorise the call. Verification is best-effort — if the
    cookie isn't valid or the API key doesn't resolve, ``None`` is
    returned (handler answers 401/403 as appropriate).
    """
    try:
        session = runtime._get_session_from_cookie(headers)  # noqa: SLF001
    except Exception:
        session = None
    if session is not None:
        user_id = str(session.get("user_id") or session.get("user") or "").strip()
        role = str(session.get("role") or "").strip()
        if user_id:
            return {
                "user_id": user_id,
                "role": role,
                "scopes": set(session.get("scopes") or ()),
                "source": "cookie",
            }

    supplied_admin_token = str(headers.get("x-admin-token") or "")
    configured_admin_token = str(getattr(runtime, "admin_ui_token", "") or "")
    if (
        supplied_admin_token
        and configured_admin_token
        and compare_digest(supplied_admin_token, configured_admin_token)
    ):
        return {
            "user_id": "admin-ui-token",
            "role": "admin",
            "scopes": {"*"},
            "source": "admin_ui_token",
        }

    raw_key = headers.get("x-api-key") or headers.get("authorization") or ""
    if raw_key:
        if raw_key.lower().startswith("bearer "):
            raw_key = raw_key[7:].strip()
        if raw_key:
            try:
                admin_identity = getattr(runtime, "admin_identity_service", None) or getattr(
                    runtime, "admin_identity", None
                )
                if admin_identity is not None and hasattr(
                    admin_identity, "resolve_dynamic_api_key"
                ):
                    profile_name = getattr(runtime, "profile_name", "") or ""
                    principal = admin_identity.resolve_dynamic_api_key(
                        token=raw_key,
                        profile_name=profile_name,
                    )
                    if principal is not None:
                        return {
                            "user_id": getattr(principal, "user_id", "") or "",
                            "role": getattr(principal, "role", "") or "",
                            "scopes": set(getattr(principal, "scopes", ()) or ()),
                            "source": "api_key",
                        }
            except Exception:
                pass

    return None


def _principal_has_wildcard(principal: dict[str, Any] | None) -> bool:
    """Return ``True`` when the principal carries the ``*`` admin wildcard."""
    if principal is None:
        return False
    role = (principal.get("role") or "").strip().lower()
    if role == "admin":
        return True
    scopes = principal.get("scopes") or ()
    return "*" in scopes


async def check_route_guard(
    runtime: Any,
    scope: Any,
    receive: Any,
    send: Any,
    *,
    method: str,
    path: str,
    headers: dict[str, str],
) -> bool:
    """The ASGI chokepoint. Return ``True`` if the request was intercepted.

    ``intercepted = True`` means the chokepoint sent a 401 and the caller
    should ``return`` immediately. ``intercepted = False`` means the
    request is allowed to continue to the existing dispatch.
    """
    if scope.get("type") != "http":
        return False

    ui_base_path = getattr(runtime, "ui_base_path", "/ui") or "/ui"
    bucket = route_guards.classify(method, path, ui_base_path=ui_base_path)

    # Pass-through buckets: existing dispatch handles auth + authz.
    if bucket in ("public", "auth", "ui", "idam_v1", "unknown"):
        return False

    # bucket == "guarded"
    # HTML SPA navigation fallback: file-mcp serves dual-mode admin
    # paths (HTML SPA shell vs JSON API) based on the Accept header.
    # Browser navigation must reach the SPA shell so the login gate can
    # render; the API short-circuit returns the JSON 401 to authed
    # callers.
    if _is_html_fallback(headers, path, ui_base_path=ui_base_path):
        return False

    if _request_carries_credentials(runtime, headers):
        # Credentials present → existing dispatch (cookie middleware +
        # MultiProfileApiKeyTokenVerifier + per-tool/per-route RBAC)
        # verifies them and decides. The chokepoint does not duplicate
        # that work.
        return False

    # Anonymous request to a guarded route → F-741-1 closure.
    await _send_status(send, 401, _denied_body("UNAUTHENTICATED", "authentication required"))
    return True


__all__ = ["check_route_guard"]
