"""Structured edit package (scaffold)."""

from .jsonyaml import (
    json_delete,
    json_get,
    json_set,
    parse_path,
    yaml_delete,
    yaml_get,
    yaml_set,
)
from .markdown import md_get_section, md_set_section
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
    "json_set",
    "md_get_section",
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
    "yaml_set",
]
