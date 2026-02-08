"""Authentication helpers for file-mcp-server.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: API key validation and FastMCP token verifier integration.
Requirements: FR1.5, CS1.1
Tasks: T3, T15
Architecture: 4.1 Authentication
Tests: UT1.2, ST1.2
Recent Change History:
- 2026-02-07: Added FastMCP token verifier with configurable header/scheme support.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Iterable, List

import time

from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection

from fastmcp.server.auth import AccessToken, TokenVerifier


class AuthError(ValueError):
    """Raised when authentication fails."""


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    key_fingerprint: str


def key_fingerprint(api_key: str) -> str:
    digest = sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


class ApiKeyAuth:
    def __init__(self, api_keys: Iterable[str]) -> None:
        self._keys: List[str] = [key for key in api_keys if key]

    def validate(self, api_key: str | None) -> AuthResult:
        if not self._keys:
            raise AuthError("No API keys configured")
        if not api_key:
            raise AuthError("Missing API key")

        for key in self._keys:
            if compare_digest(key, api_key):
                return AuthResult(ok=True, key_fingerprint=key_fingerprint(api_key))

        raise AuthError("Invalid API key")


class HeaderTokenAuthBackend(AuthenticationBackend):
    """Authentication backend for configurable token headers and schemes."""

    def __init__(self, token_verifier: TokenVerifier, *, header_name: str, header_scheme: str | None) -> None:
        self.token_verifier = token_verifier
        self.header_name = header_name.lower()
        self.header_scheme = header_scheme

    @staticmethod
    def _extract_token(raw_header: str, scheme: str | None) -> str | None:
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

    async def authenticate(self, conn: HTTPConnection):
        raw_header = conn.headers.get(self.header_name)
        if not raw_header:
            return None

        token = self._extract_token(raw_header, self.header_scheme)
        if not token:
            return None

        auth_info = await self.token_verifier.verify_token(token)
        if not auth_info:
            return None

        if auth_info.expires_at and auth_info.expires_at < int(time.time()):
            return None

        return AuthCredentials(auth_info.scopes), AuthenticatedUser(auth_info)


class ApiKeyTokenVerifier(TokenVerifier):
    """FastMCP token verifier backed by configured API keys."""

    def __init__(
        self,
        api_keys: Iterable[str],
        *,
        header_name: str | None = None,
        header_scheme: str | None = None,
        required_scopes: list[str] | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes)
        self._api_key_auth = ApiKeyAuth(api_keys)
        normalized_header_name = self._normalize_optional_text(header_name)
        normalized_header_scheme = self._normalize_optional_text(header_scheme)
        self.header_name = (normalized_header_name or "authorization").strip().lower()
        if normalized_header_scheme is None and self.header_name == "authorization":
            self.header_scheme = "Bearer"
        else:
            self.header_scheme = normalized_header_scheme

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or "${" in cleaned:
            return None
        return cleaned

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            result = self._api_key_auth.validate(token)
        except AuthError:
            return None

        return AccessToken(
            token=result.key_fingerprint,
            client_id="file-mcp-client",
            scopes=list(self.required_scopes or []),
            claims={"fingerprint": result.key_fingerprint},
        )

    def get_middleware(self) -> list:
        return [
            Middleware(
                AuthenticationMiddleware,  # type: ignore[arg-type]
                backend=HeaderTokenAuthBackend(
                    self,
                    header_name=self.header_name,
                    header_scheme=self.header_scheme,
                ),
            ),
            Middleware(AuthContextMiddleware),  # type: ignore[arg-type]
        ]
