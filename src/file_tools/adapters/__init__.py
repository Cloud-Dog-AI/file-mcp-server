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
