"""Filesystem IO package (scaffold)."""

from .encoding import b64_decode, b64_encode
from .filesystem import (
    atomic_write,
    copy_file,
    delete_file,
    list_dir,
    move_file,
    normalize_paths,
    read_bytes,
    read_text,
    write_bytes,
    write_text,
)

__all__ = [
    "b64_decode",
    "b64_encode",
    "atomic_write",
    "copy_file",
    "delete_file",
    "list_dir",
    "move_file",
    "normalize_paths",
    "read_bytes",
    "read_text",
    "write_bytes",
    "write_text",
]
