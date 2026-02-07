"""Meld integration scaffolding."""

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import Popen
from typing import Tuple


def meld_available() -> bool:
    return which("meld") is not None


def launch_meld(path_a: Path, path_b: Path) -> Tuple[bool, str]:
    if not meld_available():
        return False, "meld not available"
    try:
        Popen(["meld", str(path_a), str(path_b)])
    except OSError as exc:
        return False, f"meld launch failed: {exc}"
    return True, "meld launched"
