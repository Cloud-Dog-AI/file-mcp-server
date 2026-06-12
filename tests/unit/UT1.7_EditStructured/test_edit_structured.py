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

"""Structured edit tests.
import pytest

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for structured edits across JSON/YAML/XML/HTML/Markdown.
Requirements: FR1.13, FR1.14, FR1.15, FR1.16
Tasks: T9
Architecture: 6.5 Structured edits
Tests: UT1.9, UT1.10, UT1.11
Recent Change History:
- 2026-02-05: Align structured edit tests to config-driven roots and CRUD depth.
"""

from __future__ import annotations

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.edit import (
    html_delete,
    html_get,
    html_set,
    json_copy,
    json_delete,
    json_get,
    json_merge,
    json_move,
    json_set,
    md_get_section,
    md_set_section,
    xml_delete,
    xml_get,
    xml_set,
    yaml_copy,
    yaml_delete,
    yaml_get,
    yaml_merge,
    yaml_move,
    yaml_set,
)


def _scoped_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    defaults_yaml = """
profiles:
  default:
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {"FILE_MCP_ROOT": str(root)}
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return Path(profile.scope.roots[0])
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_json_yaml_crud(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    json_path = root / "data.json"
    yaml_path = root / "data.yaml"
    json_path.write_text('{"a": {"b": [1, 2]}}', encoding="utf-8")
    yaml_path.write_text("a:\n  b:\n    - 1\n    - 2\n", encoding="utf-8")

    json_source = json_path.read_text(encoding="utf-8")
    json_updated = json_set(json_source, "/a/b/1", 3)
    assert json_get(json_updated, "/a/b/1") == 3
    assert json_set(json_source, "/a/b/1", 3) == json_updated
    json_updated = json_delete(json_updated, "/a/b/0")
    assert json_get(json_updated, "/a/b/0") == 3
    assert json_updated.strip().startswith("{")

    yaml_updated = yaml_set(yaml_path.read_text(encoding="utf-8"), "/a/b/0", 9)
    assert yaml_get(yaml_updated, "/a/b/0") == 9
    yaml_updated = yaml_delete(yaml_updated, "/a/b/1")
    assert yaml_get(yaml_updated, "/a/b/0") == 9
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_json_yaml_move_copy_merge_matrix(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    json_path = root / "matrix.json"
    yaml_path = root / "matrix.yaml"
    json_path.write_text('{"a":{"b":1},"c":{}}', encoding="utf-8")
    yaml_path.write_text("a:\n  b: 1\nc: {}\n", encoding="utf-8")

    json_text = json_path.read_text(encoding="utf-8")
    json_text = json_copy(json_text, "/a/b", "/c/copied")
    assert json_get(json_text, "/c/copied") == 1
    json_text = json_move(json_text, "/c/copied", "/a/moved")
    assert json_get(json_text, "/a/moved") == 1
    json_text = json_merge(json_text, "/a", {"merged": {"x": 9}})
    assert json_get(json_text, "/a/merged/x") == 9

    yaml_text = yaml_path.read_text(encoding="utf-8")
    yaml_text = yaml_copy(yaml_text, "/a/b", "/c/copied")
    assert yaml_get(yaml_text, "/c/copied") == 1
    yaml_text = yaml_move(yaml_text, "/c/copied", "/a/moved")
    assert yaml_get(yaml_text, "/a/moved") == 1
    yaml_text = yaml_merge(yaml_text, "/a", {"merged": {"x": 9}})
    assert yaml_get(yaml_text, "/a/merged/x") == 9
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_xml_html_edits(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    xml_path = root / "data.xml"
    html_path = root / "data.html"
    xml_path.write_text("<root><item>old</item></root>", encoding="utf-8")
    html_path.write_text("<html><body><p>old</p></body></html>", encoding="utf-8")

    xml_updated = xml_set(xml_path.read_text(encoding="utf-8"), "/root/item", "new")
    assert "new" in xml_updated
    assert "item" in (xml_get(xml_updated, "/root/item") or "")
    xml_deleted = xml_delete(xml_updated, "/root/item")
    assert xml_get(xml_deleted, "/root/item") is None

    try:
        xml_set(xml_updated, "/root/missing", "value")
    except ValueError as exc:
        assert "XPath" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for missing XML XPath")

    html_updated = html_set(html_path.read_text(encoding="utf-8"), "p", "new")
    assert "new" in html_updated
    assert "p" in (html_get(html_updated, "p") or "")
    html_deleted = html_delete(html_updated, "p")
    assert html_get(html_deleted, "p") is None

    try:
        html_set(html_updated, ".missing", "value")
    except ValueError as exc:
        assert "Selector" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for missing HTML selector")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_markdown_section_edits(tmp_path: Path) -> None:
    root = _scoped_root(tmp_path)
    md_path = root / "doc.md"
    md_path.write_text("# Title\n\nHello\n\n## Details\n\nMore", encoding="utf-8")
    text = md_path.read_text(encoding="utf-8")

    section = md_get_section(text, "Title")
    assert section and section.startswith("# Title")
    updated = md_set_section(text, "Details", "## Details\n\nUpdated")
    assert "Updated" in updated
    inserted = md_set_section(updated, "Missing", "## Missing\n\nAdded")
    assert inserted.strip().endswith("Added")
