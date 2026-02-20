"""Compatibility re-exports for IDAM-backed authentication.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Backwards-compatible auth module forwarding to idam_adapter.
Requirements: FR1.5, CS1.1
Tasks: T3, T15
Architecture: 4.1 Authentication
Tests: UT1.2, ST1.2
Recent Change History:
- 2026-02-20: Replaced bespoke module body with idam_adapter re-exports.
"""

from __future__ import annotations

from .idam_adapter import (
    ApiKeyAuth,
    ApiKeyTokenVerifier,
    AuthError,
    AuthResult,
    HeaderTokenAuthBackend,
    MultiProfileApiKeyTokenVerifier,
    get_request_profile_name,
    key_digest,
    key_fingerprint,
    set_request_profile_name,
)

__all__ = [
    "ApiKeyAuth",
    "ApiKeyTokenVerifier",
    "AuthError",
    "AuthResult",
    "HeaderTokenAuthBackend",
    "MultiProfileApiKeyTokenVerifier",
    "get_request_profile_name",
    "key_digest",
    "key_fingerprint",
    "set_request_profile_name",
]
