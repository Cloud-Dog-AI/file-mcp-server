"""
file-mcp-server — file_tools/io/encoding.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for io encoding.py.
"""

from __future__ import annotations

import base64


def b64_encode(data: bytes, *, urlsafe: bool = False) -> str:
    """Execute b64 encode."""
    encoder = base64.urlsafe_b64encode if urlsafe else base64.b64encode
    return encoder(data).decode("ascii")


def b64_decode(data: str, *, urlsafe: bool = False) -> bytes:
    """Execute b64 decode."""
    decoder = base64.urlsafe_b64decode if urlsafe else base64.b64decode
    return decoder(data.encode("ascii"))
