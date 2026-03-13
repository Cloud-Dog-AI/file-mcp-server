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

"""Structured edit package (scaffold)."""

from .jsonyaml import (
    json_copy,
    json_delete,
    json_get,
    json_merge,
    json_move,
    json_set,
    parse_path,
    yaml_copy,
    yaml_delete,
    yaml_get,
    yaml_merge,
    yaml_move,
    yaml_set,
)
from .markdown import md_get_section, md_set_frontmatter, md_set_section
from .sedlike import (
    EditResult,
    apply_edits,
    delete_matching_lines,
    insert_after_line,
    insert_before_line,
    replace_line_range,
    replace_regex,
)
from .xmlhtml import html_delete, html_get, html_set, xml_delete, xml_get, xml_set

__all__ = [
    "html_delete",
    "html_get",
    "html_set",
    "json_delete",
    "json_get",
    "json_copy",
    "json_merge",
    "json_move",
    "json_set",
    "md_get_section",
    "md_set_frontmatter",
    "md_set_section",
    "EditResult",
    "apply_edits",
    "delete_matching_lines",
    "insert_after_line",
    "insert_before_line",
    "replace_line_range",
    "replace_regex",
    "parse_path",
    "xml_delete",
    "xml_get",
    "xml_set",
    "yaml_delete",
    "yaml_get",
    "yaml_copy",
    "yaml_merge",
    "yaml_move",
    "yaml_set",
]
