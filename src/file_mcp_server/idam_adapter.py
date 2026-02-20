"""IDAM adapter for file-mcp-server authentication.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: FastMCP token-verifier bridge using cloud_dog_idam providers and RBAC.
Requirements: FR1.5, CS1.1
Tasks: T3, T15
Architecture: 4.1 Authentication
Tests: UT1.2, ST1.2
Recent Change History:
- 2026-02-20: Replaced bespoke API-key verification flow with cloud_dog_idam adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Any, Iterable, List, Mapping, Protocol, cast

import contextvars
import time

from cloud_dog_idam import (  # type: ignore[import-not-found,import-untyped]
    APIKeyOnlyProvider,
    ProviderRegistry,
    RBACEngine,
)
from cloud_dog_idam.api_keys.hashing import hash_api_key  # type: ignore[import-not-found,import-untyped]
from cloud_dog_idam.audit.emitter import AuditEmitter  # type: ignore[import-not-found,import-untyped]
from cloud_dog_idam.audit.models import AuditEvent  # type: ignore[import-not-found,import-untyped]
from cloud_dog_idam.domain.errors import AuthenticationError  # type: ignore[import-not-found,import-untyped]
from cloud_dog_idam.domain.models import (  # type: ignore[import-not-found,import-untyped]
    AuthRequest as IDAMAuthRequest,
)
from fastmcp.server.auth import AccessToken, TokenVerifier
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection


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


def key_digest(api_key: str) -> str:
    digest = sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


# Backwards-compatible export for existing imports/tests.
key_fingerprint = key_digest


class ApiKeyAuth:
    """Compatibility helper retained for tests and non-runtime usage."""

    def __init__(self, api_keys: Iterable[str]) -> None:
        self._keys: List[str] = [key for key in api_keys if key]
        self._key_hashes = [hash_api_key(key) for key in self._keys]

    def validate(self, api_key: str | None) -> AuthResult:
        if not self._keys:
            raise AuthError("No API keys configured")
        if not api_key:
            raise AuthError("Missing API key")
        candidate_hash = hash_api_key(api_key)
        for key_hash in self._key_hashes:
            if compare_digest(candidate_hash, key_hash):
                return AuthResult(ok=True, key_fingerprint=key_digest(api_key))
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

    def _record_failure(
        self,
        *,
        reason: str,
        conn: HTTPConnection,
        profile_name: str | None = None,
    ) -> None:
        recorder = getattr(self.token_verifier, "record_auth_failure", None)
        if callable(recorder):
            recorder(reason=reason, conn=conn, profile_name=profile_name)

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
                self._record_failure(
                    reason="missing_credentials", conn=conn, profile_name=profile_name
                )
                return None
            token = self._extract_token(raw_header, header_scheme)
            if not token:
                self._record_failure(
                    reason="malformed_credentials", conn=conn, profile_name=profile_name
                )
                return None
            auth_info = await profile_verifier.verify_token_for_profile(
                token, profile_name
            )
            if not auth_info:
                self._record_failure(
                    reason="invalid_credentials", conn=conn, profile_name=profile_name
                )
                return None
            if auth_info.expires_at and auth_info.expires_at < int(time.time()):
                self._record_failure(
                    reason="expired_credentials", conn=conn, profile_name=profile_name
                )
                return None
            return AuthCredentials(auth_info.scopes), AuthenticatedUser(auth_info)

        raw_header = conn.headers.get(self.header_name)
        if not raw_header:
            self._record_failure(reason="missing_credentials", conn=conn)
            return None

        token = self._extract_token(raw_header, self.header_scheme)
        if not token:
            self._record_failure(reason="malformed_credentials", conn=conn)
            return None

        auth_info = await self.token_verifier.verify_token(token)
        if not auth_info:
            self._record_failure(reason="invalid_credentials", conn=conn)
            return None

        if auth_info.expires_at and auth_info.expires_at < int(time.time()):
            self._record_failure(reason="expired_credentials", conn=conn)
            return None

        return AuthCredentials(auth_info.scopes), AuthenticatedUser(auth_info)


class _IDAMAuditMixin:
    """Common helpers for IDAM-backed verifier audit emission."""

    def _normalise_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or "${" in cleaned:
            return None
        return cleaned

    def _correlation_id(self, conn: HTTPConnection | None) -> str:
        if conn is None:
            return ""
        return (
            conn.headers.get("x-correlation-id")
            or conn.headers.get("x-request-id")
            or ""
        )

    def _emit_audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_id: str,
        details: dict[str, Any],
        conn: HTTPConnection | None = None,
    ) -> None:
        emitter = getattr(self, "_audit_emitter", None)
        if emitter is not None:
            emitter.emit(
                AuditEvent(
                    actor_id=actor_id,
                    action=action,
                    outcome=outcome,
                    correlation_id=self._correlation_id(conn),
                    details=details,
                )
            )

        logger = getattr(self, "_logger", None)
        if logger is not None:
            payload = {
                "event": "idam_auth",
                "action": action,
                "outcome": outcome,
                **details,
            }
            if outcome == "success":
                logger.info("IDAM auth event", **payload)
            else:
                logger.warning("IDAM auth event", **payload)

    @staticmethod
    def _normalise_fingerprint(value: str) -> str:
        if value.startswith("sha256:"):
            return value
        return f"sha256:{value[:12]}"


class ApiKeyTokenVerifier(_IDAMAuditMixin, TokenVerifier):
    """FastMCP token verifier backed by cloud_dog_idam API-key provider."""

    def __init__(
        self,
        api_keys: Iterable[str],
        *,
        header_name: str | None = None,
        header_scheme: str | None = None,
        required_scopes: list[str] | None = None,
        audit_emitter: AuditEmitter | None = None,
        logger: Any | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes)
        self._keys: List[str] = [key for key in api_keys if key]
        self._logger = logger
        self._audit_emitter = audit_emitter
        role_permissions = {
            "viewer": {"profile:default"},
            "admin": {"*"},
        }
        self._rbac_engine = RBACEngine(role_permissions=role_permissions)
        self._provider = APIKeyOnlyProvider(
            key_role_mapping={key: "viewer" for key in self._keys},
            default_role="viewer",
        )
        self._registry = ProviderRegistry()
        self._registry.register(self._provider, priority=10)
        normalised_header_name = self._normalise_optional_text(header_name)
        normalised_header_scheme = self._normalise_optional_text(header_scheme)
        self.header_name = (normalised_header_name or "authorization").strip().lower()
        self.header_scheme: str | None
        if normalised_header_scheme is None and self.header_name == "authorization":
            self.header_scheme = "Bearer"
        else:
            self.header_scheme = normalised_header_scheme

    def record_auth_failure(
        self,
        *,
        reason: str,
        conn: HTTPConnection | None = None,
        profile_name: str | None = None,
    ) -> None:
        details: dict[str, Any] = {"reason": reason}
        if profile_name:
            details["profile"] = profile_name
        self._emit_audit(
            action="authenticate",
            outcome="failure",
            actor_id="anonymous",
            details=details,
            conn=conn,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            result = await self._registry.authenticate(
                IDAMAuthRequest(auth_type="api_key_only", secret=token)
            )
        except AuthenticationError:
            self._emit_audit(
                action="authenticate",
                outcome="failure",
                actor_id="anonymous",
                details={"reason": "invalid_api_key"},
            )
            return None

        user = result.user
        role = str(user.role or "viewer")
        self._rbac_engine.assign_role_to_user(user.user_id, role)
        permissions = set(self._rbac_engine.get_effective_permissions(user.user_id))
        scopes = list(self.required_scopes or [])
        for permission in sorted(permissions):
            if permission not in scopes:
                scopes.append(permission)
        fingerprint = self._normalise_fingerprint(
            str(result.claims.get("fingerprint", ""))
        )
        self._emit_audit(
            action="authenticate",
            outcome="success",
            actor_id=user.user_id,
            details={
                "role": role,
                "profile": "default",
                "fingerprint": fingerprint,
            },
        )
        return AccessToken(
            token=fingerprint,
            client_id=user.user_id or "file-mcp-client",
            scopes=scopes,
            claims={
                "fingerprint": fingerprint,
                "role": role,
                "permissions": sorted(permissions),
                "profile": "default",
            },
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


@dataclass(frozen=True)
class _ProfileAuthState:
    registry: ProviderRegistry
    header_name: str
    header_scheme: str | None
    role_name: str


class MultiProfileApiKeyTokenVerifier(_IDAMAuditMixin, TokenVerifier):
    """Profile-aware API-key verifier backed by cloud_dog_idam."""

    def __init__(
        self,
        profile_auth: Mapping[str, tuple[Iterable[str], str | None, str | None]],
        *,
        default_profile: str,
        profile_header_name: str = "x-file-mcp-profile",
        profile_query_name: str = "profile",
        required_scopes: list[str] | None = None,
        audit_emitter: AuditEmitter | None = None,
        logger: Any | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes)
        if default_profile not in profile_auth:
            raise ValueError(
                f"default profile '{default_profile}' missing from profile_auth"
            )

        self.default_profile = default_profile
        self.profile_header_name = profile_header_name.strip().lower()
        self.profile_query_name = profile_query_name.strip()
        self._logger = logger
        self._audit_emitter = audit_emitter
        role_permissions: dict[str, set[str]] = {"admin": {"*"}}
        self._profiles: dict[str, _ProfileAuthState] = {}

        for profile_name, (
            api_keys,
            header_name,
            header_scheme,
        ) in profile_auth.items():
            role_name = f"profile:{profile_name}:role"
            role_permissions[role_name] = {f"profile:{profile_name}"}
            normalised_header_name = self._normalise_optional_text(header_name)
            normalised_header_scheme = self._normalise_optional_text(header_scheme)
            final_header_name = (
                (normalised_header_name or "authorization").strip().lower()
            )
            if (
                normalised_header_scheme is None
                and final_header_name == "authorization"
            ):
                final_header_scheme: str | None = "Bearer"
            else:
                final_header_scheme = normalised_header_scheme

            provider = APIKeyOnlyProvider(
                key_role_mapping={key: role_name for key in api_keys if key},
                default_role=role_name,
            )
            registry = ProviderRegistry()
            registry.register(provider, priority=10)
            self._profiles[profile_name] = _ProfileAuthState(
                registry=registry,
                header_name=final_header_name,
                header_scheme=final_header_scheme,
                role_name=role_name,
            )

        self._rbac_engine = RBACEngine(role_permissions=role_permissions)

    def _resolve_profile_from_path(self, path: str) -> str | None:
        # Optional path selector format: /mcp/<profile>/...
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0].lower() == "mcp":
            candidate = parts[1].strip()
            if candidate in self._profiles:
                return candidate
        return None

    def resolve_profile(self, conn: HTTPConnection) -> str:
        query_candidate = conn.query_params.get(self.profile_query_name)
        if query_candidate and query_candidate in self._profiles:
            self._emit_audit(
                action="profile_select",
                outcome="success",
                actor_id="anonymous",
                details={"profile": query_candidate, "source": "query"},
                conn=conn,
            )
            return query_candidate

        header_candidate = conn.headers.get(self.profile_header_name)
        if header_candidate and header_candidate in self._profiles:
            self._emit_audit(
                action="profile_select",
                outcome="success",
                actor_id="anonymous",
                details={"profile": header_candidate, "source": "header"},
                conn=conn,
            )
            return header_candidate

        path_candidate = self._resolve_profile_from_path(conn.url.path or "")
        if path_candidate:
            self._emit_audit(
                action="profile_select",
                outcome="success",
                actor_id="anonymous",
                details={"profile": path_candidate, "source": "path"},
                conn=conn,
            )
            return path_candidate

        self._emit_audit(
            action="profile_select",
            outcome="success",
            actor_id="anonymous",
            details={"profile": self.default_profile, "source": "default"},
            conn=conn,
        )
        return self.default_profile

    def header_for_profile(self, profile_name: str) -> tuple[str, str | None]:
        state = self._profiles[profile_name]
        return state.header_name, state.header_scheme

    def record_auth_failure(
        self,
        *,
        reason: str,
        conn: HTTPConnection | None = None,
        profile_name: str | None = None,
    ) -> None:
        details: dict[str, Any] = {"reason": reason}
        if profile_name:
            details["profile"] = profile_name
        self._emit_audit(
            action="authenticate",
            outcome="failure",
            actor_id="anonymous",
            details=details,
            conn=conn,
        )

    async def verify_token_for_profile(
        self, token: str, profile_name: str
    ) -> AccessToken | None:
        state = self._profiles.get(profile_name)
        if state is None:
            self._emit_audit(
                action="authenticate",
                outcome="failure",
                actor_id="anonymous",
                details={"reason": "unknown_profile", "profile": profile_name},
            )
            return None

        try:
            result = await state.registry.authenticate(
                IDAMAuthRequest(
                    auth_type="api_key_only",
                    secret=token,
                    metadata={"profile": profile_name},
                )
            )
        except AuthenticationError:
            self._emit_audit(
                action="authenticate",
                outcome="failure",
                actor_id="anonymous",
                details={"reason": "invalid_api_key", "profile": profile_name},
            )
            return None

        user = result.user
        role = str(user.role or state.role_name)
        self._rbac_engine.assign_role_to_user(user.user_id, role)
        required_permission = f"profile:{profile_name}"
        if not self._rbac_engine.has_permission(user.user_id, required_permission):
            self._emit_audit(
                action="authorise",
                outcome="failure",
                actor_id=user.user_id,
                details={
                    "reason": "profile_permission_denied",
                    "profile": profile_name,
                    "role": role,
                },
            )
            return None

        permissions = set(self._rbac_engine.get_effective_permissions(user.user_id))
        scopes = list(self.required_scopes or [])
        for permission in sorted(permissions):
            if permission not in scopes:
                scopes.append(permission)
        if required_permission not in scopes:
            scopes.append(required_permission)

        fingerprint = self._normalise_fingerprint(
            str(result.claims.get("fingerprint", ""))
        )
        self._emit_audit(
            action="authenticate",
            outcome="success",
            actor_id=user.user_id,
            details={
                "profile": profile_name,
                "role": role,
                "fingerprint": fingerprint,
            },
        )
        return AccessToken(
            token=fingerprint,
            client_id=user.user_id or "file-mcp-client",
            scopes=scopes,
            claims={
                "fingerprint": fingerprint,
                "profile": profile_name,
                "role": role,
                "permissions": sorted(permissions),
            },
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        # Fallback for interfaces that do not pass request context.
        return await self.verify_token_for_profile(token, self.default_profile)

    def get_middleware(self) -> list:
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
