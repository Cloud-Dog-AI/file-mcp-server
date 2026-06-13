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

"""Base64 encoding tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for base64 encode/decode helpers.
Requirements: FR1.10
Tasks: T7
Architecture: 6.3 Base64
Tests: UT1.6
Recent Change History:
- 2026-02-05: Added header for base64 tests.
"""


from __future__ import annotations
import pytest

from file_tools.io import b64_decode, b64_encode
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_b64_encode_decode_roundtrip() -> None:
    encoded = b64_encode(b"hello")
    assert encoded == "aGVsbG8="
    assert b64_decode(encoded) == b"hello"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_b64_urlsafe_roundtrip() -> None:
    encoded = b64_encode(b"hello?", urlsafe=True)
    assert b64_decode(encoded, urlsafe=True) == b"hello?"
