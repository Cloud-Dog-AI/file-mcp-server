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
file-mcp-server — file_tools/audit/snapshots.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for audit snapshots.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from cloud_dog_storage import path_utils
from cloud_dog_storage.backends.local import LocalStorage


def _snapshot_storage(base_dir: Path) -> LocalStorage:
    """Build a LocalStorage instance rooted at *base_dir*."""
    return LocalStorage(root_path=base_dir, min_free_bytes=0)


def snapshot_path(base_dir: Path, source: Path) -> Path:
    """Execute snapshot path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = path_utils.to_posix(str(source)).lstrip("/")
    return base_dir / timestamp / relative


def create_snapshot(base_dir: Path, source: Path) -> Path:
    """Create snapshot preserving source file metadata via cloud_dog_storage."""
    target = snapshot_path(base_dir, source)
    path_utils.copy_with_metadata(str(source), str(target))
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
    """Create snapshot bytes via LocalStorage."""
    storage = _snapshot_storage(base_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = logical_path.lstrip("/")
    storage_key = f"{timestamp}/{relative}"
    storage.write_bytes(storage_key, data)
    return base_dir / timestamp / relative


def _snapshot_dirs(base_dir: Path) -> list[Path]:
    """Handle snapshot dirs via cloud_dog_storage path_utils."""
    if not path_utils.exists(str(base_dir)):
        return []
    entries: list[tuple[datetime, Path]] = []
    for child_str in path_utils.iter_dir(str(base_dir)):
        if not path_utils.is_dir(child_str):
            continue
        child_name = path_utils.name(child_str)
        try:
            stamp = datetime.strptime(child_name, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        entries.append((stamp, path_utils.as_path(child_str)))
    entries.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in entries]


def _dir_size_bytes(path: Path) -> int:
    """Compute aggregate byte size via cloud_dog_storage path_utils."""
    total = 0
    for file_str in path_utils.rglob(str(path), "*"):
        if path_utils.is_file(file_str):
            try:
                total += path_utils.file_stat(file_str).st_size
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

    storage = _snapshot_storage(base_dir)
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
                storage.delete_path(entry.name, missing_ok=True)
                entries.remove(entry)
                removed += 1

    if (
        retention_count is not None
        and retention_count >= 0
        and len(entries) > retention_count
    ):
        for entry in entries[retention_count:]:
            storage.delete_path(entry.name, missing_ok=True)
            removed += 1
        entries = entries[:retention_count]

    if max_storage_mb is not None and max_storage_mb >= 0:
        max_bytes = max_storage_mb * 1024 * 1024
        total_bytes = sum(_dir_size_bytes(entry) for entry in entries)
        idx = len(entries) - 1
        while total_bytes > max_bytes and idx >= 0:
            entry = entries[idx]
            size = _dir_size_bytes(entry)
            storage.delete_path(entry.name, missing_ok=True)
            removed += 1
            total_bytes -= size
            idx -= 1

    return removed
