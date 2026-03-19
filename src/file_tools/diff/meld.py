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

"""
file-mcp-server — file_tools/diff/meld.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for diff meld.py.
"""

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import Popen
from typing import Tuple


def meld_available() -> bool:
    """Execute meld available."""
    return which("meld") is not None


def launch_meld(path_a: Path, path_b: Path) -> Tuple[bool, str]:
    """Execute launch meld."""
    if not meld_available():
        return False, "meld not available"
    try:
        Popen(["meld", str(path_a), str(path_b)])
    except OSError as exc:
        return False, f"meld launch failed: {exc}"
    return True, "meld launched"
