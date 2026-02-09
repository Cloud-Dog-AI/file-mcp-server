"""Filesystem IO package (scaffold)."""

from .encoding import b64_decode, b64_encode
from .filesystem import (
    atomic_write,
    chmod_path,
    copy_file,
    create_dir,
    delete_file,
    list_dir,
    move_file,
    move_path,
    normalize_paths,
    read_bytes,
    read_text,
    rename_path,
    write_bytes,
    write_text,
)

__all__ = [
    "b64_decode",
    "b64_encode",
    "atomic_write",
    "chmod_path",
    "copy_file",
    "create_dir",
    "delete_file",
    "list_dir",
    "move_file",
    "move_path",
    "normalize_paths",
    "read_bytes",
    "read_text",
    "rename_path",
    "write_bytes",
    "write_text",
]
