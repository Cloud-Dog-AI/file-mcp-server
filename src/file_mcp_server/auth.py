# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# """
# License: Apache 2.0
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
