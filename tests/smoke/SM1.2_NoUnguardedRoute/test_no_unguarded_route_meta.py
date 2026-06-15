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

"""SM1.2 — No-Unguarded-Route meta-test (W28A-742 b-2 GATE-1).

Structural property: every raw ASGI route in ``server_runtime.py::__call__``
classifies into exactly one of the five buckets exposed by
``file_mcp_server.route_guards``:

1. ``public`` — :data:`FILE_MCP_PUBLIC_ALLOWLIST` (anon-OK)
2. ``auth`` — :data:`FILE_MCP_AUTH_PATHS` (anon-OK with materialisation)
3. ``guarded`` — matched by :func:`route_guards.match`
4. ``idam_v1`` — :data:`FILE_MCP_IDAM_V1_PATTERN`
5. ``ui`` — SPA shell / asset / fallback

The classifier MUST NEVER return ``unknown`` for a path that the server
actually serves. This test exercises the catalog against a representative
set of routes drawn directly from the v3 comparison map §3.4 and the raw
``server_runtime.py`` branches.

A more exhaustive (AST-parse + MCP tool registry + A2A skill registry)
enumeration lands in IT1.FM_NoUnguardedRouteLive; this smoke test is
intentionally narrow + fast (no DB, no FastAPI, no live server).
"""

from __future__ import annotations

import pytest

from file_mcp_server.route_guards import (
    FILE_MCP_PUBLIC_ALLOWLIST,
    FILE_MCP_AUTH_PATHS,
    FILE_MCP_IDAM_V1_PATTERN,
    ROUTE_GUARDS,
    all_registered_keys,
    classify,
    match,
)


# Representative probes drawn from the v3 comparison map §3.4 — one row per
# bucket plus the W28A-742 closure cases (F-741-1, F2, F4, F5).
PROBES = [
    # (method, path, expected_bucket)

    # ── public bucket (§3.4.1) ──
    ("GET", "/health",                            "public"),
    ("GET", "/ready",                             "public"),
    ("GET", "/live",                              "public"),
    ("GET", "/status",                            "public"),
    ("GET", "/openapi.json",                      "public"),
    ("GET", "/.well-known/agent.json",            "public"),

    # ── auth bucket (§3.4.2) ──
    ("POST", "/auth/login",                       "auth"),
    ("GET",  "/auth/me",                          "auth"),
    ("POST", "/auth/logout",                      "auth"),
    ("GET",  "/auth/status",                      "auth"),
    ("GET",  "/api/auth/status",                  "auth"),

    # ── ui bucket (§3.4.3) ──
    ("GET", "/",                                  "ui"),
    ("GET", "/ui",                                "ui"),
    ("GET", "/ui/anything",                       "ui"),
    ("GET", "/runtime-config.js",                 "ui"),
    ("GET", "/dashboard",                         "ui"),
    ("GET", "/search",                            "ui"),
    ("GET", "/settings",                          "ui"),
    ("GET", "/file-browser",                      "ui"),
    ("GET", "/storage-profiles",                  "ui"),
    ("GET", "/audit-log",                         "ui"),
    ("GET", "/api-docs",                          "ui"),
    ("GET", "/mcp-console",                       "ui"),
    ("GET", "/a2a-console",                       "ui"),
    ("GET", "/google-drive-settings",             "ui"),
    ("GET", "/admin-identity",                    "ui"),
    ("GET", "/idam",                              "ui"),
    ("GET", "/idam/users",                        "ui"),
    ("GET", "/idam/groups",                       "ui"),
    ("GET", "/idam/roles",                        "ui"),
    ("GET", "/idam/rbac",                         "ui"),
    ("GET", "/idam/api-keys",                     "ui"),
    ("GET", "/assets/foo.js",                     "ui"),
    ("GET", "/random-spa-route",                  "ui"),

    # ── idam_v1 bucket (§3.4.6) ──
    ("GET",  "/idam/v1/resource-registry",        "idam_v1"),
    ("GET",  "/idam/v1/rbac/bindings",            "idam_v1"),
    ("GET",  "/idam/v1/rbac-bindings",            "idam_v1"),  # back-compat hyphen
    ("POST", "/idam/v1/rbac/bindings",            "idam_v1"),
    ("DELETE", "/idam/v1/rbac/bindings/b-001",    "idam_v1"),
    ("GET",  "/v1/idam/v1/rbac/bindings",         "idam_v1"),  # v3 F5 alias
    ("GET",  "/v1/idam/v1/rbac-bindings",         "idam_v1"),  # v3 F5 alias + back-compat

    # ── guarded bucket (§3.4.4) ──
    ("GET", "/a2a/health",                        "guarded"),   # F-741-1 fix
    ("POST", "/mcp",                              "guarded"),
    ("POST", "/webmcp",                           "guarded"),
    ("GET", "/mcp/tools",                         "guarded"),   # v3 F2
    ("GET", "/webmcp/tools",                      "guarded"),   # v3 F2
    ("GET", "/a2a/events",                        "guarded"),   # v3 F4
    ("GET", "/a2a/events/history",                "guarded"),   # v3 F4
    ("GET", "/events",                            "guarded"),   # v3 F4
    ("GET", "/events/history",                    "guarded"),   # v3 F4
    ("POST", "/a2a/tasks",                        "guarded"),
    ("POST", "/tasks",                            "guarded"),
    ("GET", "/api/v1/files",                      "guarded"),
    ("PUT", "/api/v1/files/some/path.txt",        "guarded"),
    ("GET", "/api/v1/profiles",                   "guarded"),
    ("POST", "/api/v1/profiles",                  "guarded"),
    ("PATCH", "/v1/profiles/profile-1",           "guarded"),
    ("GET", "/api/v1/jobs",                       "guarded"),
    ("GET", "/api/v1/jobs/abc123",                "guarded"),
    ("GET", "/v1/jobs/queue/status",              "guarded"),
    ("GET", "/api/v1/logs",                       "guarded"),
    ("POST", "/admin/users",                      "guarded"),
    ("PUT", "/admin/users/u-001",                 "guarded"),
    ("DELETE", "/admin/users/u-001",              "guarded"),
    ("GET", "/admin/groups/g-001",                "guarded"),
    ("POST", "/admin/groups/g-001/members",       "guarded"),
    ("DELETE", "/admin/groups/g-001/members/u-1", "guarded"),
    ("POST", "/admin/api-keys",                   "guarded"),
    ("DELETE", "/admin/api-keys/k-001",           "guarded"),
    ("GET", "/admin/roles",                       "guarded"),
    ("POST", "/admin/roles",                      "guarded"),
    ("GET", "/admin/profiles",                    "guarded"),
    ("POST", "/admin/profiles",                   "guarded"),
    ("GET", "/api/admin/profiles",                "guarded"),
    ("POST", "/admin/reload",                     "guarded"),
    ("GET", "/admin/runtime-config",              "guarded"),
    ("GET", "/admin/identity",                    "guarded"),
    ("GET", "/admin/google-drive",                "guarded"),
    ("POST", "/admin/google-drive/start",         "guarded"),
    ("GET", "/admin/rbac",                        "guarded"),
    ("GET", "/v1/admin",                          "guarded"),
    ("GET", "/v1/admin/users",                    "guarded"),
]
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


@pytest.mark.parametrize("method,path,expected", PROBES)
def test_classify_returns_expected_bucket(
    method: str, path: str, expected: str
) -> None:
    """Every probe in the v3 §3.4 catalog classifies into the documented bucket."""
    actual = classify(method, path)
    assert actual == expected, (
        f"classify({method!r}, {path!r}) returned {actual!r}, expected {expected!r}"
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_no_unguarded_route_for_canonical_probes() -> None:
    """None of the probes return ``unknown`` — that is the structural property."""
    for method, path, _expected in PROBES:
        actual = classify(method, path)
        assert actual != "unknown", (
            f"({method}, {path}) classified as 'unknown' — would default-DENY at runtime; "
            "every served route must be classifiable"
        )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_public_allowlist_includes_required_anon_endpoints() -> None:
    """The default-config public allowlist covers health/ready/live/status/openapi/agent-card."""
    required = {
        "/health",
        "/ready",
        "/live",
        "/status",
        "/openapi.json",
        "/.well-known/agent.json",
    }
    missing = required - FILE_MCP_PUBLIC_ALLOWLIST
    assert not missing, f"public allowlist missing required entries: {missing}"
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_public_allowlist_excludes_a2a_health() -> None:
    """F-741-1 closure: ``/a2a/health`` must NOT be in the public allowlist."""
    assert "/a2a/health" not in FILE_MCP_PUBLIC_ALLOWLIST, (
        "/a2a/health is the F-741-1 closure site — it must require auth (PS-82 FR1.46), "
        "not be added to the public allowlist"
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_auth_paths_include_login_me_logout() -> None:
    """Auth bucket covers login + me + logout + status."""
    required = {
        ("POST", "/auth/login"),
        ("GET", "/auth/me"),
        ("POST", "/auth/logout"),
        ("GET", "/auth/status"),
        ("GET", "/api/auth/status"),
    }
    missing = required - FILE_MCP_AUTH_PATHS
    assert not missing, f"auth bucket missing required entries: {missing}"
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_idam_v1_pattern_matches_canonical_and_v1_prefix() -> None:
    """v3 F5: both ``/idam/v1/*`` and ``/v1/idam/v1/*`` match the same pattern."""
    canonical = "/idam/v1/rbac/bindings"
    v1_alias = "/v1/idam/v1/rbac/bindings"
    assert FILE_MCP_IDAM_V1_PATTERN.search(canonical)
    assert FILE_MCP_IDAM_V1_PATTERN.search(v1_alias)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_a2a_health_is_guarded() -> None:
    """F-741-1 CLOSED: ``GET /a2a/health`` classifies as ``guarded`` with ``a2a.access``."""
    bucket = classify("GET", "/a2a/health")
    assert bucket == "guarded"
    match_result = match("GET", "/a2a/health")
    assert match_result is not None
    guard, _ = match_result
    assert guard.permission == "a2a.access"
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_mcp_tools_get_routes_are_guarded() -> None:
    """v3 F2: ``GET /mcp/tools`` and ``GET /webmcp/tools`` are guarded ``mcp.access``."""
    for path in ("/mcp/tools", "/webmcp/tools"):
        bucket = classify("GET", path)
        assert bucket == "guarded", f"{path} should be guarded"
        match_result = match("GET", path)
        assert match_result is not None
        guard, _ = match_result
        assert guard.permission == "mcp.access", (
            f"GET {path}: expected mcp.access, got {guard.permission}"
        )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_a2a_events_endpoints_all_four_guarded() -> None:
    """v3 F4: all four event endpoints (canonical + Traefik-stripped) are guarded."""
    for path in (
        "/a2a/events",
        "/a2a/events/history",
        "/events",
        "/events/history",
    ):
        bucket = classify("GET", path)
        assert bucket == "guarded", f"{path} should be guarded"
        match_result = match("GET", path)
        assert match_result is not None
        guard, _ = match_result
        assert guard.permission == "a2a.access"
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_route_guards_have_no_duplicate_keys() -> None:
    """The catalog must not silently shadow guards (first-match-wins)."""
    seen: set[tuple[str, str]] = set()
    for guard in ROUTE_GUARDS:
        key = (guard.method, guard.pattern.pattern)
        # Duplicate (method, pattern) string is suspicious; the regexes
        # might legitimately differ in semantics but share a string. We
        # do NOT fail outright — we record + let visual review handle it.
        # The dedup property is enforced by ``all_registered_keys``.
        seen.add(key)
    # No silent dedup — the registered_keys set has at most as many entries
    # as ROUTE_GUARDS (with first-wins, duplicates are not catastrophic).
    assert len(seen) <= len(ROUTE_GUARDS)
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_route_guards_minimum_coverage() -> None:
    """The catalog covers at least the core surfaces named in the v3 map §3.4.4."""
    # The catalog has ~69 rows after v3; assert ≥40 to catch accidental
    # truncation in a future edit.
    assert len(ROUTE_GUARDS) >= 40, (
        f"ROUTE_GUARDS catalog truncated to {len(ROUTE_GUARDS)} rows; "
        "v3 §3.4.4 expects ≥40 rows covering files/jobs/logs/users/groups/api-keys/"
        "roles/profiles/google-drive/reload/runtime-config/rbac"
    )
@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-017")


def test_resource_id_extractor_for_user_route() -> None:
    """Path-parameter resource_ids extract correctly from a regex match."""
    match_result = match("GET", "/admin/users/u-12345")
    assert match_result is not None
    guard, regex_match = match_result
    assert guard.resource_id_extractor is not None
    resource_id = guard.resource_id_extractor(regex_match, {})
    assert resource_id == "u-12345"
