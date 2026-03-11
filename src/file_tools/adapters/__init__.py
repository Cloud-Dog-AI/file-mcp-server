"""Shared third-party adapter interfaces.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Centralised adapters that isolate direct external library imports.
Requirements: FR1.3
Tasks: W25A-B
Architecture: 4.3 External service interface pattern
Tests: QT1.1, QT1.2
"""

from .http_client import (
    ConnectionError,
    HTTPError,
    RequestException,
    Response,
    Timeout,
    basic_auth,
    get,
    post,
    request,
)
from .yaml_codec import YAMLError, safe_dump, safe_load

__all__ = [
    "ConnectionError",
    "HTTPError",
    "RequestException",
    "Response",
    "Timeout",
    "YAMLError",
    "basic_auth",
    "get",
    "post",
    "request",
    "safe_dump",
    "safe_load",
]
