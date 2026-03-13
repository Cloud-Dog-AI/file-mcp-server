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
