from __future__ import annotations

from pathlib import Path


def project_root(start: Path) -> Path:
    """Resolve the repository root from any nested test file path."""
    resolved = start.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / "src").is_dir() and (candidate / "RULES.md").is_file():
            return candidate
    raise RuntimeError(f"Unable to locate repository root from: {start}")
