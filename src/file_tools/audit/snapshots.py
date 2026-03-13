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
file-mcp-server — file_tools/audit/snapshots.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for audit snapshots.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import shutil


def snapshot_path(base_dir: Path, source: Path) -> Path:
    """Execute snapshot path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = source.as_posix().lstrip("/")
    return base_dir / timestamp / relative


def create_snapshot(base_dir: Path, source: Path) -> Path:
    """Create snapshot."""
    target = snapshot_path(base_dir, source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def snapshot_path_for_logical(base_dir: Path, logical_path: str) -> Path:
    """
    Build a snapshot path for a logical (non-local) path.

    logical_path should be a POSIX absolute path (e.g. `/docs/a.txt`).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = logical_path.lstrip("/")
    return base_dir / timestamp / relative


def create_snapshot_bytes(base_dir: Path, logical_path: str, data: bytes) -> Path:
    """Create snapshot bytes."""
    target = snapshot_path_for_logical(base_dir, logical_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def _snapshot_dirs(base_dir: Path) -> list[Path]:
    """Handle snapshot dirs."""
    if not base_dir.exists():
        return []
    entries: list[tuple[datetime, Path]] = []
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        try:
            stamp = datetime.strptime(entry.name, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        entries.append((stamp, entry))
    entries.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in entries]


def _dir_size_bytes(path: Path) -> int:
    """Handle dir size bytes."""
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def prune_snapshots(
    base_dir: Path,
    retention_days: int | None,
    retention_count: int | None = None,
    max_storage_mb: int | None = None,
) -> int:
    """Execute prune snapshots."""
    entries = _snapshot_dirs(base_dir)
    if not entries:
        return 0

    now = datetime.now(timezone.utc)
    removed = 0

    if retention_days is not None and retention_days >= 0:
        for entry in list(entries):
            try:
                stamp = datetime.strptime(entry.name, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            if (now - stamp).days > retention_days:
                shutil.rmtree(entry, ignore_errors=True)
                entries.remove(entry)
                removed += 1

    if (
        retention_count is not None
        and retention_count >= 0
        and len(entries) > retention_count
    ):
        for entry in entries[retention_count:]:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
        entries = entries[:retention_count]

    if max_storage_mb is not None and max_storage_mb >= 0:
        max_bytes = max_storage_mb * 1024 * 1024
        total_bytes = sum(_dir_size_bytes(entry) for entry in entries)
        idx = len(entries) - 1
        while total_bytes > max_bytes and idx >= 0:
            entry = entries[idx]
            size = _dir_size_bytes(entry)
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
            total_bytes -= size
            idx -= 1

    return removed
