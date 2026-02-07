"""Authentication scaffolding (API key validation)."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Iterable, List


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
