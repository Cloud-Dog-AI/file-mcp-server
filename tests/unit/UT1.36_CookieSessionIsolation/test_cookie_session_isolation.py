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

# UT1.36 — W28E-1837 regression: cookie-session isolation / anonymous negative-auth (CS-001, FR-024).
# A credential-less (cookieless / non-matching-cookie) request to _get_session_from_cookie MUST
# resolve to None (anonymous → 401/{user:null}). It must NEVER inherit the most-recent active
# session: the previous "cookie session fallback" leaked an admin principal to anonymous callers
# after any admin login. See server_runtime.py:_get_session_from_cookie.

from __future__ import annotations

import time

import pytest

from file_mcp_server.server_runtime import HealthCheckMiddleware


def _middleware(sessions: dict) -> HealthCheckMiddleware:
    mw = HealthCheckMiddleware.__new__(HealthCheckMiddleware)
    mw._cookie_name = "fmsession"
    mw._sessions = sessions
    return mw


@pytest.mark.UT
@pytest.mark.webui
@pytest.mark.negative
@pytest.mark.req("CS-001")
@pytest.mark.req("FR-024")
def test_cookieless_request_is_anonymous_even_with_active_admin_session(monkeypatch) -> None:
    # Reproduce the leaky condition: auth_mode defaults to "cookie", an admin session is active.
    monkeypatch.setenv("FILE_MCP_UI_AUTH_MODE", "cookie")
    monkeypatch.delenv("FILE_MCP_UI_COOKIE_SESSION_FALLBACK", raising=False)
    sessions = {
        "tok-admin": {"user_id": "1", "user": "admin", "role": "admin", "_created": time.time()},
    }
    mw = _middleware(sessions)
    # No cookie header at all → anonymous.
    assert mw._get_session_from_cookie({}) is None
    # A cookie that does not match any stored session token → anonymous (no global fallback).
    assert mw._get_session_from_cookie({"cookie": "other=x; theme=dark"}) is None


@pytest.mark.UT
@pytest.mark.webui
@pytest.mark.negative
@pytest.mark.req("CS-001")
@pytest.mark.req("FR-024")
def test_explicit_fallback_flag_does_not_reintroduce_anon_leak(monkeypatch) -> None:
    # Even with the legacy opt-in flag set, a cookieless caller must not inherit a session.
    monkeypatch.setenv("FILE_MCP_UI_COOKIE_SESSION_FALLBACK", "1")
    monkeypatch.setenv("FILE_MCP_UI_AUTH_MODE", "cookie")
    sessions = {
        "tok-admin": {"user_id": "1", "user": "admin", "role": "admin", "_created": time.time()},
    }
    mw = _middleware(sessions)
    assert mw._get_session_from_cookie({}) is None


@pytest.mark.UT
@pytest.mark.webui
@pytest.mark.req("FR-024")
def test_valid_matching_cookie_returns_own_session() -> None:
    sessions = {
        "tok-admin": {"user_id": "1", "user": "admin", "role": "admin", "_created": time.time()},
    }
    mw = _middleware(sessions)
    sess = mw._get_session_from_cookie({"cookie": "fmsession=tok-admin"})
    assert sess is not None
    assert sess["role"] == "admin"


@pytest.mark.UT
@pytest.mark.webui
@pytest.mark.negative
@pytest.mark.req("CS-001")
@pytest.mark.req("FR-024")
def test_expired_matching_cookie_is_anonymous() -> None:
    sessions = {
        "tok-old": {"user_id": "1", "user": "admin", "role": "admin", "_created": time.time() - 7200},
    }
    mw = _middleware(sessions)
    assert mw._get_session_from_cookie({"cookie": "fmsession=tok-old"}) is None
