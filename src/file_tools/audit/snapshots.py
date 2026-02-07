"""Snapshot manager scaffolding."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import shutil


def snapshot_path(base_dir: Path, source: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = source.as_posix().lstrip("/")
    return base_dir / timestamp / relative


def create_snapshot(base_dir: Path, source: Path) -> Path:
    target = snapshot_path(base_dir, source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
