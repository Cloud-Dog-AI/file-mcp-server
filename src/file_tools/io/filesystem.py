"""Safe filesystem operations scaffolding."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, List

from filelock import FileLock


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)


def _lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def atomic_write(path: Path, data: bytes, *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Target already exists: {path}")
    ensure_parent(path)
    lock = FileLock(str(_lock_path(path)))
    with lock:
        if path.exists() and not overwrite:
            raise FileExistsError(f"Target already exists: {path}")
        with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)
        os.replace(temp_path, path)


def write_bytes(path: Path, data: bytes, *, overwrite: bool = True) -> None:
    atomic_write(path, data, overwrite=overwrite)


def write_text(path: Path, content: str, *, encoding: str = "utf-8", overwrite: bool = True) -> None:
    atomic_write(path, content.encode(encoding), overwrite=overwrite)


def copy_file(src: Path, dst: Path, *, overwrite: bool = False) -> None:
    if dst.exists() and not overwrite:
        raise FileExistsError(f"Target already exists: {dst}")
    ensure_parent(dst)
    if dst.exists() and overwrite:
        dst.unlink()
    shutil.copy2(src, dst)


def _remove_existing_target(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def move_path(src: Path, dst: Path, *, overwrite: bool = False) -> None:
    if dst.exists() and not overwrite:
        raise FileExistsError(f"Target already exists: {dst}")
    ensure_parent(dst)
    if dst.exists() and overwrite:
        _remove_existing_target(dst)
    shutil.move(str(src), str(dst))


def move_file(src: Path, dst: Path, *, overwrite: bool = False) -> None:
    move_path(src, dst, overwrite=overwrite)


def rename_path(src: Path, dst: Path, *, overwrite: bool = False) -> None:
    move_path(src, dst, overwrite=overwrite)


def create_dir(path: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
    path.mkdir(parents=parents, exist_ok=exist_ok)


def chmod_path(path: Path, mode: int, *, recursive: bool = False) -> None:
    os.chmod(path, mode)
    if recursive and path.is_dir():
        for dirpath, dirnames, filenames in os.walk(path):
            current = Path(dirpath)
            for name in dirnames:
                os.chmod(current / name, mode)
            for name in filenames:
                os.chmod(current / name, mode)


def delete_file(path: Path, *, missing_ok: bool = False) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        if not missing_ok:
            raise


def list_dir(path: Path, *, recursive: bool = False) -> List[Path]:
    if recursive:
        return [item for item in path.rglob("*")]
    return list(path.iterdir())


def normalize_paths(paths: Iterable[Path]) -> List[Path]:
    return [path.resolve() for path in paths]
