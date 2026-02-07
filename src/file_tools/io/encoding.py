"""Encoding helpers scaffolding."""

from __future__ import annotations

import base64


def b64_encode(data: bytes, *, urlsafe: bool = False) -> str:
    encoder = base64.urlsafe_b64encode if urlsafe else base64.b64encode
    return encoder(data).decode("ascii")


def b64_decode(data: str, *, urlsafe: bool = False) -> bytes:
    decoder = base64.urlsafe_b64decode if urlsafe else base64.b64decode
    return decoder(data.encode("ascii"))
