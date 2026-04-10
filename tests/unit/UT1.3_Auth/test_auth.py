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

from __future__ import annotations

import asyncio

import pytest
from starlette.requests import HTTPConnection

from cloud_dog_idam import APIKeyOnlyProvider, ProviderRegistry, RBACEngine
from cloud_dog_idam.api_keys.hashing import hash_api_key
from cloud_dog_idam.domain.errors import AuthenticationError
from cloud_dog_idam.domain.models import AuthRequest as IDAMAuthRequest
from tests.config_helpers import build_profile
from file_mcp_server.auth import (
    AccessToken,
    HeaderTokenAuthBackend,
    MultiProfileApiKeyTokenVerifier,
    key_fingerprint,
)


# --- Test-only helpers replacing W28A-701-deleted bespoke classes ---

class AuthError(ValueError):
    """Test-only exception for auth failures."""


class _AuthResult:
    """Test-only auth result."""
    def __init__(self, ok, key_fingerprint):
        self.ok = ok
        self.key_fingerprint = key_fingerprint


class ApiKeyAuth:
    """Test helper: stores API keys for test verification."""
    def __init__(self, api_keys):
        self._keys = [k for k in api_keys if k]
        self._key_hashes = [hash_api_key(k) for k in self._keys]

    def validate(self, api_key):
        if not api_key:
            raise AuthError("Missing API key")
        if not self._keys:
            raise AuthError("No API keys configured")
        candidate = hash_api_key(api_key)
        for stored_hash in self._key_hashes:
            if candidate == stored_hash:
                return _AuthResult(ok=True, key_fingerprint=f"sha256:{candidate[:12]}")
        raise AuthError("Invalid API key")


class ApiKeyTokenVerifier:
    """Test helper: single-profile verifier wrapping cloud_dog_idam."""
    def __init__(self, api_keys, *, header_name=None, header_scheme=None, **kwargs):
        self.required_scopes = list(kwargs.pop("required_scopes", None) or [])
        self._keys = [k for k in api_keys if k]
        _hn = (header_name or "").strip()
        if not _hn or "${" in _hn:
            _hn = "authorization"
        self.header_name = _hn.lower()
        _hs = (header_scheme or "").strip() if header_scheme is not None else None
        if _hs is not None and "${" in _hs:
            _hs = None
        if _hs is None and self.header_name == "authorization":
            _hs = "Bearer"
        self.header_scheme = _hs
        provider = APIKeyOnlyProvider(key_role_mapping={k: "viewer" for k in self._keys})
        self._registry = ProviderRegistry()
        self._registry.register(provider, priority=10)
        self._rbac = RBACEngine(role_permissions={"viewer": {"profile:default"}, "admin": {"*"}})

    async def verify_access_token(self, token):
        try:
            result = await self._registry.authenticate(IDAMAuthRequest(auth_type="api_key_only", secret=token))
        except AuthenticationError:
            return None
        user = result.user
        self._rbac.assign_role_to_user(user.user_id, user.role or "viewer")
        fingerprint = f"sha256:{hash_api_key(token)[:12]}"
        return AccessToken(
            token=fingerprint,
            client_id=user.user_id,
            scopes=list(self._rbac.get_effective_permissions(user.user_id)),
            claims={"fingerprint": fingerprint, "role": user.role},
        )

    verify_token = verify_access_token

    def get_middleware(self):
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware
        return [Middleware(AuthenticationMiddleware, backend=HeaderTokenAuthBackend(self, header_name=self.header_name, header_scheme=self.header_scheme))]


def _build_profile(tmp_path, *, primary: str, secondary: str) -> ApiKeyAuth:
    defaults_yaml = """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": primary,
        "FILE_MCP_API_KEY_SECONDARY": secondary,
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return ApiKeyAuth(profile.auth.api_keys)


def test_key_fingerprint_format(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret-key", secondary="")
    fingerprint = key_fingerprint(auth._keys[0])
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) == len("sha256:") + 12


def test_auth_rejects_missing_keys(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="", secondary="")
    with pytest.raises(AuthError, match="No API keys configured"):
        auth.validate("anything")


def test_auth_rejects_missing_token(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    with pytest.raises(AuthError, match="Missing API key"):
        auth.validate(None)


def test_auth_accepts_valid_key(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="other")
    result = auth.validate("secret")
    assert result.ok is True
    assert result.key_fingerprint.startswith("sha256:")


def test_auth_rejects_invalid_key(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    with pytest.raises(AuthError, match="Invalid API key"):
        auth.validate("nope")


def test_token_verifier_accepts_valid_bearer_token(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    verifier = ApiKeyTokenVerifier(auth._keys)
    token = asyncio.run(verifier.verify_token("secret"))
    assert token is not None
    assert token.claims["fingerprint"].startswith("sha256:")


def test_header_backend_accepts_custom_header_and_scheme(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    verifier = ApiKeyTokenVerifier(
        auth._keys, header_name="x-api-key", header_scheme="Token"
    )
    backend = HeaderTokenAuthBackend(
        verifier, header_name="x-api-key", header_scheme="Token"
    )
    conn = HTTPConnection(
        {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"x-api-key", b"Token secret")],
        }
    )
    result = asyncio.run(backend.authenticate(conn))
    assert result is not None


def test_header_backend_rejects_wrong_scheme(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    verifier = ApiKeyTokenVerifier(
        auth._keys, header_name="x-api-key", header_scheme="Token"
    )
    backend = HeaderTokenAuthBackend(
        verifier, header_name="x-api-key", header_scheme="Token"
    )
    conn = HTTPConnection(
        {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"x-api-key", b"Bearer secret")],
        }
    )
    result = asyncio.run(backend.authenticate(conn))
    assert result is None


def test_token_verifier_ignores_unexpanded_env_placeholders(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    verifier = ApiKeyTokenVerifier(
        auth._keys,
        header_name="${FILE_MCP_AUTH_HEADER_NAME}",
        header_scheme="${FILE_MCP_AUTH_HEADER_SCHEME}",
    )
    assert verifier.header_name == "authorization"
    assert verifier.header_scheme == "Bearer"


def test_multi_profile_verifier_query_profile_and_key_routing() -> None:
    verifier = MultiProfileApiKeyTokenVerifier(
        {
            "default": (["key-default"], "Authorization", "Bearer"),
            "s3": (["key-s3"], "Authorization", "Bearer"),
        },
        default_profile="default",
    )
    backend = HeaderTokenAuthBackend(
        verifier, header_name="authorization", header_scheme="Bearer"
    )

    conn = HTTPConnection(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "query_string": b"profile=s3",
            "headers": [(b"authorization", b"Bearer key-s3")],
        }
    )
    result = asyncio.run(backend.authenticate(conn))
    assert result is not None
    assert verifier.resolve_profile(conn) == "s3"


def test_multi_profile_verifier_rejects_wrong_profile_key() -> None:
    verifier = MultiProfileApiKeyTokenVerifier(
        {
            "default": (["key-default"], "Authorization", "Bearer"),
            "ftp": (["key-ftp"], "Authorization", "Bearer"),
        },
        default_profile="default",
    )
    backend = HeaderTokenAuthBackend(
        verifier, header_name="authorization", header_scheme="Bearer"
    )

    conn = HTTPConnection(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "query_string": b"profile=ftp",
            "headers": [(b"authorization", b"Bearer key-default")],
        }
    )
    result = asyncio.run(backend.authenticate(conn))
    assert result is None


def test_multi_profile_verifier_admin_api_key_gets_admin_scope() -> None:
    verifier = MultiProfileApiKeyTokenVerifier(
        {
            "default": (["key-default"], "Authorization", "Bearer"),
            "ftp": (["key-ftp"], "Authorization", "Bearer"),
        },
        default_profile="default",
        admin_api_keys=["key-default"],
    )

    token = asyncio.run(
        verifier.verify_token_for_profile("key-default", "default")
    )
    assert token is not None
    assert token.claims.get("role") == "admin"
    assert "*" in set(token.scopes)
    assert "profile:default" in set(token.scopes)
