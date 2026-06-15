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

"""Search utility tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for search utilities and limits.
Requirements: FR1.9, NF1.2, CS1.5
Tasks: T6, T18
Architecture: 6.2 Search, 7.2 Performance
Tests: UT1.5, ST1.7
Recent Change History:
- 2026-02-05: Added limit coverage for search utilities.
"""


from __future__ import annotations
import pytest

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.search import SearchMatch, search_content, search_paths


def _build_profile(
    tmp_path: Path, *, max_results: int, max_file_mb: int, allow_glob: str
):
    root = tmp_path / "root"
    defaults_yaml = """
profiles:
  default:
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
      allow_globs:
        - "${FILE_MCP_ALLOW_GLOB}"
    limits:
      search_max_results: "${FILE_MCP_SEARCH_MAX_RESULTS}"
      search_max_file_mb: "${FILE_MCP_SEARCH_MAX_FILE_MB}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_ROOT": str(root),
        "FILE_MCP_ALLOW_GLOB": allow_glob,
        "FILE_MCP_SEARCH_MAX_RESULTS": str(max_results),
        "FILE_MCP_SEARCH_MAX_FILE_MB": str(max_file_mb),
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return profile, root
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_paths(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=10, max_file_mb=5, allow_glob="**/*"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("alpha")
    (root / "beta.md").write_text("beta")

    matches = search_paths("alpha", roots=[Path(profile.scope.roots[0])])
    assert any(path.name == "alpha.txt" for path in matches)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_paths_glob(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=10, max_file_mb=5, allow_glob="**/*.md"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("alpha")
    (root / "beta.md").write_text("beta")

    matches = search_paths(
        "", roots=[Path(profile.scope.roots[0])], glob=profile.scope.allow_globs[0]
    )
    assert {path.name for path in matches} == {"beta.md"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_content(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=10, max_file_mb=5, allow_glob="**/*"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("alpha\nline")
    (root / "beta.txt").write_text("beta\nalpha")

    results = search_content("alpha", roots=[Path(profile.scope.roots[0])])
    assert results
    assert all(isinstance(result, SearchMatch) for result in results)
    assert any(result.path.name == "beta.txt" for result in results)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_content_regex(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=10, max_file_mb=5, allow_glob="**/*"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("foo123")

    results = search_content(
        r"foo\d+", roots=[Path(profile.scope.roots[0])], regex=True
    )
    assert len(results) == 1
    assert results[0].line == "foo123"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_content_max_results(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=1, max_file_mb=5, allow_glob="**/*"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("alpha")
    (root / "beta.txt").write_text("alpha")

    results = search_content(
        "alpha",
        roots=[Path(profile.scope.roots[0])],
        max_results=profile.limits.search_max_results,
    )
    assert len(results) == 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-019")


def test_search_content_max_file_mb(tmp_path: Path) -> None:
    profile, root = _build_profile(
        tmp_path, max_results=10, max_file_mb=1, allow_glob="**/*"
    )
    root.mkdir(parents=True, exist_ok=True)
    small = root / "small.txt"
    large = root / "large.txt"
    small.write_text("alpha")
    max_mb = profile.limits.search_max_file_mb or 1
    large.write_text("alpha" + ("x" * (max_mb * 1024 * 1024 + 1)))

    results = search_content(
        "alpha",
        roots=[Path(profile.scope.roots[0])],
        max_file_mb=profile.limits.search_max_file_mb,
    )
    assert all(result.path != large for result in results)
    assert any(result.path == small for result in results)
