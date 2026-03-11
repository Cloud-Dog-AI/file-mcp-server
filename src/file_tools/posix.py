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
    return Path(path).expanduser().resolve()


def to_posix(path: str | Path) -> str:
    """Execute to posix."""
    return Path(path).as_posix()


def safe_join(root: Path, *parts: str) -> Path:
    """Execute safe join."""
    candidate = root.joinpath(*parts).resolve()
    try:
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError("Path escapes root")
    except AttributeError:
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("Path escapes root") from exc
    return candidate


def require_relative(path: Path) -> None:
    """Execute require relative."""
    if path.is_absolute():
        raise ValueError("Path must be relative")


def filter_posix_paths(paths: Iterable[Path]) -> list[Path]:
    """Execute filter posix paths."""
    return [path for path in paths if is_posix_path(path)]
