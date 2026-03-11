"""HTTP client adapter for external requests library usage.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Single adapter module for outbound HTTP calls and request exceptions.
Requirements: FR1.3
Tasks: W25A-B
Architecture: 4.3 External service interface pattern
Tests: QT1.1, QT1.2
"""

from __future__ import annotations

from typing import Any

import requests
from requests import Response
from requests.auth import HTTPBasicAuth

Timeout = requests.Timeout
ConnectionError = requests.ConnectionError
HTTPError = requests.HTTPError
RequestException = requests.RequestException


def request(method: str, url: str, **kwargs: Any) -> Response:
    """Send an HTTP request through the shared adapter surface."""
    return requests.request(method, url, **kwargs)


def get(url: str, **kwargs: Any) -> Response:
    """Send a GET request through the shared adapter surface."""
    return requests.get(url, **kwargs)


def post(url: str, **kwargs: Any) -> Response:
    """Send a POST request through the shared adapter surface."""
    return requests.post(url, **kwargs)


def basic_auth(username: str, password: str) -> HTTPBasicAuth:
    """Return a basic-auth helper object for request authentication."""
    return HTTPBasicAuth(username, password)
