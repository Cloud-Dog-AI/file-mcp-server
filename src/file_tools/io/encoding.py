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
