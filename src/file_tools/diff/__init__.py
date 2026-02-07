"""Diff package (scaffold)."""

from .diffgen import diff_files, diff_lines, diff_text
from .meld import launch_meld, meld_available

__all__ = [
    "diff_files",
    "diff_lines",
    "diff_text",
    "launch_meld",
    "meld_available",
]
