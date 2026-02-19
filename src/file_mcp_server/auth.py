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
from typing import Iterable, List, Mapping, Protocol, cast

import contextvars
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


class MultiProfileTokenVerifierProtocol(Protocol):
    def resolve_profile(self, conn: HTTPConnection) -> str: ...

    def header_for_profile(self, profile_name: str) -> tuple[str, str | None]: ...

    async def verify_token_for_profile(
        self, token: str, profile_name: str
    ) -> AccessToken | None: ...


_request_profile_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "file_mcp_request_profile_name", default=None
)


def set_request_profile_name(profile_name: str) -> None:
    _request_profile_name.set(profile_name)


def get_request_profile_name(default: str | None = None) -> str | None:
    value = _request_profile_name.get()
    if value:
        return value
    return default


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

    def __init__(
        self,
        token_verifier: TokenVerifier,
        *,
        header_name: str,
        header_scheme: str | None,
    ) -> None:
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
        if (
            hasattr(self.token_verifier, "resolve_profile")
            and hasattr(self.token_verifier, "header_for_profile")
            and hasattr(self.token_verifier, "verify_token_for_profile")
        ):
            profile_verifier = cast(
                MultiProfileTokenVerifierProtocol, self.token_verifier
            )
            profile_name = profile_verifier.resolve_profile(conn)
            set_request_profile_name(profile_name)
            header_name, header_scheme = profile_verifier.header_for_profile(
                profile_name
            )
            raw_header = conn.headers.get(header_name)
            if not raw_header:
                return None
            token = self._extract_token(raw_header, header_scheme)
            if not token:
                return None
            auth_info = await profile_verifier.verify_token_for_profile(
                token, profile_name
            )
            if not auth_info:
                return None
            if auth_info.expires_at and auth_info.expires_at < int(time.time()):
                return None
            return AuthCredentials(auth_info.scopes), AuthenticatedUser(auth_info)

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
        final_header_scheme: str | None
        if normalized_header_scheme is None and self.header_name == "authorization":
            final_header_scheme = "Bearer"
        else:
            final_header_scheme = normalized_header_scheme
        self.header_scheme = final_header_scheme

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


class MultiProfileApiKeyTokenVerifier(TokenVerifier):
    """Profile-aware API key verifier for single-process multi-profile runtime."""

    def __init__(
        self,
        profile_auth: Mapping[str, tuple[Iterable[str], str | None, str | None]],
        *,
        default_profile: str,
        profile_header_name: str = "x-file-mcp-profile",
        profile_query_name: str = "profile",
        required_scopes: list[str] | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes)
        if default_profile not in profile_auth:
            raise ValueError(
                f"default profile '{default_profile}' missing from profile_auth"
            )

        self.default_profile = default_profile
        self.profile_header_name = profile_header_name.strip().lower()
        self.profile_query_name = profile_query_name.strip()
        self._profile_auth: dict[str, ApiKeyAuth] = {}
        self._profile_header: dict[str, str] = {}
        self._profile_scheme: dict[str, str | None] = {}

        for profile_name, (
            api_keys,
            header_name,
            header_scheme,
        ) in profile_auth.items():
            normalized_header_name = self._normalize_optional_text(header_name)
            normalized_header_scheme = self._normalize_optional_text(header_scheme)
            final_header_name = (
                (normalized_header_name or "authorization").strip().lower()
            )
            final_header_scheme: str | None
            if (
                normalized_header_scheme is None
                and final_header_name == "authorization"
            ):
                final_header_scheme = "Bearer"
            else:
                final_header_scheme = normalized_header_scheme
            self._profile_auth[profile_name] = ApiKeyAuth(api_keys)
            self._profile_header[profile_name] = final_header_name
            self._profile_scheme[profile_name] = final_header_scheme

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or "${" in cleaned:
            return None
        return cleaned

    def _resolve_profile_from_path(self, path: str) -> str | None:
        # Optional path selector format: /mcp/<profile>/...
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0].lower() == "mcp":
            candidate = parts[1].strip()
            if candidate in self._profile_auth:
                return candidate
        return None

    def resolve_profile(self, conn: HTTPConnection) -> str:
        query_candidate = conn.query_params.get(self.profile_query_name)
        if query_candidate and query_candidate in self._profile_auth:
            return query_candidate

        header_candidate = conn.headers.get(self.profile_header_name)
        if header_candidate and header_candidate in self._profile_auth:
            return header_candidate

        path_candidate = self._resolve_profile_from_path(conn.url.path or "")
        if path_candidate:
            return path_candidate

        return self.default_profile

    def header_for_profile(self, profile_name: str) -> tuple[str, str | None]:
        return self._profile_header[profile_name], self._profile_scheme[profile_name]

    async def verify_token_for_profile(
        self, token: str, profile_name: str
    ) -> AccessToken | None:
        auth = self._profile_auth.get(profile_name)
        if auth is None:
            return None
        try:
            result = auth.validate(token)
        except AuthError:
            return None

        scopes = list(self.required_scopes or [])
        if f"profile:{profile_name}" not in scopes:
            scopes.append(f"profile:{profile_name}")
        return AccessToken(
            token=result.key_fingerprint,
            client_id="file-mcp-client",
            scopes=scopes,
            claims={"fingerprint": result.key_fingerprint, "profile": profile_name},
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        # Fallback for interfaces that do not pass request context.
        return await self.verify_token_for_profile(token, self.default_profile)

    def get_middleware(self) -> list:
        # HeaderTokenAuthBackend will call resolve_profile/header_for_profile/
        # verify_token_for_profile when available on the verifier.
        return [
            Middleware(
                AuthenticationMiddleware,  # type: ignore[arg-type]
                backend=HeaderTokenAuthBackend(
                    self,
                    header_name="authorization",
                    header_scheme="Bearer",
                ),
            ),
            Middleware(AuthContextMiddleware),  # type: ignore[arg-type]
        ]
