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

from file_tools.io import b64_decode, b64_encode


def test_b64_encode_decode_roundtrip() -> None:
    encoded = b64_encode(b"hello")
    assert encoded == "aGVsbG8="
    assert b64_decode(encoded) == b"hello"


def test_b64_urlsafe_roundtrip() -> None:
    encoded = b64_encode(b"hello?", urlsafe=True)
    assert b64_decode(encoded, urlsafe=True) == b"hello?"
