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
file-mcp-server — file_tools/posix.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for posix.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import os

from cloud_dog_storage import path_utils


def is_posix_path(path: str | Path) -> bool:
    """Return whether posix path."""
    raw = str(path)
    if os.name == "nt":
        return False
    if "\\" in raw:
        return False
    if ":" in raw and not raw.startswith(":"):
        return False
    return True


def normalize_path(path: str | Path) -> Path:
    """Normalise path."""
    return path_utils.as_path(path_utils.resolve_path(str(path)))


def to_posix(path: str | Path) -> str:
    """Execute to posix."""
    return path_utils.to_posix(str(path))


def safe_join(root: Path, *parts: str) -> Path:
    """Execute safe join."""
    candidate_str = path_utils.resolve_path(str(root.joinpath(*parts)))
    root_str = path_utils.resolve_path(str(root))
    if not path_utils.is_relative_to(candidate_str, root_str):
        raise ValueError("Path escapes root")
    return path_utils.as_path(candidate_str)


def require_relative(path: Path) -> None:
    """Execute require relative."""
    if path_utils.is_absolute(str(path)):
        raise ValueError("Path must be relative")


def filter_posix_paths(paths: Iterable[Path]) -> list[Path]:
    """Execute filter posix paths."""
    return [path for path in paths if is_posix_path(path)]
