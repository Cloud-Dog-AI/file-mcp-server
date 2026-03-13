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

from tests.config_helpers import build_profile
from file_mcp_server.auth import (
    ApiKeyAuth,
    ApiKeyTokenVerifier,
    AuthError,
    HeaderTokenAuthBackend,
    MultiProfileApiKeyTokenVerifier,
    key_fingerprint,
)


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
