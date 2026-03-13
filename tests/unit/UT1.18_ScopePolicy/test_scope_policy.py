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

from __future__ import annotations

from pathlib import Path


from tests.config_helpers import build_profile
from file_tools.scope import ScopePolicy


def _build_profile(
    tmp_path: Path,
    *,
    root: Path,
    allow_glob: str,
    deny_glob: str,
    allowed_ext: str,
    read_only_ext: str,
):
    defaults_yaml = """
profiles:
  default:
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
      allow_globs:
        - "${FILE_MCP_ALLOW_GLOB}"
      deny_globs:
        - "${FILE_MCP_DENY_GLOB}"
      allowed_exts:
        - "${FILE_MCP_ALLOWED_EXT}"
      read_only_exts:
        - "${FILE_MCP_READ_ONLY_EXT}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_ROOT": str(root),
        "FILE_MCP_ALLOW_GLOB": allow_glob,
        "FILE_MCP_DENY_GLOB": deny_glob,
        "FILE_MCP_ALLOWED_EXT": allowed_ext,
        "FILE_MCP_READ_ONLY_EXT": read_only_ext,
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )


def test_scope_denies_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    profile = _build_profile(
        tmp_path,
        root=root,
        allow_glob="**/*",
        deny_glob="**/*.secret",
        allowed_ext=".txt",
        read_only_ext=".md",
    )
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )

    decision = policy.check(tmp_path / "other.txt")
    assert not decision.allowed
    assert decision.reason == "outside_roots"


def test_scope_denies_glob(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    profile = _build_profile(
        tmp_path,
        root=root,
        allow_glob="**/*",
        deny_glob="**/*.secret",
        allowed_ext=".txt",
        read_only_ext=".md",
    )
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )

    decision = policy.check(root / "hidden.secret")
    assert not decision.allowed
    assert decision.reason == "denied_glob"


def test_scope_allows_glob(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    profile = _build_profile(
        tmp_path,
        root=root,
        allow_glob="**/*.txt",
        deny_glob="**/*.secret",
        allowed_ext=".txt",
        read_only_ext=".md",
    )
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )

    decision = policy.check(root / "notes.txt")
    assert decision.allowed
    assert decision.reason == "allowed"


def test_scope_denies_extension(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    profile = _build_profile(
        tmp_path,
        root=root,
        allow_glob="**/*",
        deny_glob="**/*.secret",
        allowed_ext=".md",
        read_only_ext=".md",
    )
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )

    decision = policy.check(root / "notes.txt")
    assert not decision.allowed
    assert decision.reason == "extension_not_allowed"


def test_scope_denies_read_only_on_write(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    profile = _build_profile(
        tmp_path,
        root=root,
        allow_glob="**/*",
        deny_glob="**/*.secret",
        allowed_ext=".md",
        read_only_ext=".md",
    )
    policy = ScopePolicy(
        roots=profile.scope.roots,
        allow_globs=profile.scope.allow_globs,
        deny_globs=profile.scope.deny_globs,
        allowed_exts=profile.scope.allowed_exts,
        read_only_exts=profile.scope.read_only_exts,
    )

    decision = policy.check(root / "notes.md", operation="write")
    assert not decision.allowed
    assert decision.reason == "extension_read_only"
