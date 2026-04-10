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
file-mcp-server — file_tools/scope/policy.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for scope policy.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from cloud_dog_storage import path_utils


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    reason: str


class ScopePolicy:
    def __init__(
        self,
        *,
        roots: Iterable[str],
        allow_globs: Iterable[str] | None = None,
        deny_globs: Iterable[str] | None = None,
        allowed_exts: Iterable[str] | None = None,
        read_only_exts: Iterable[str] | None = None,
    ) -> None:
        """Initialise the instance state."""
        self.roots = [path_utils.resolve_path(root) for root in roots]
        self.allow_globs = list(allow_globs or ["**/*"])
        self.deny_globs = list(deny_globs or [])
        self.allowed_exts = [ext.lower() for ext in (allowed_exts or [])]
        self.read_only_exts = [ext.lower() for ext in (read_only_exts or [])]

    def normalize(self, path: str) -> str:
        """Execute normalize."""
        raw = str(path or "").strip()
        if not raw or raw == ".":
            if self.roots:
                return self.roots[0]
            return path_utils.resolve_path(".")
        if path_utils.is_absolute(raw):
            return path_utils.resolve_path(raw)
        if self.roots:
            return path_utils.resolve_path(path_utils.join(self.roots[0], raw))
        return path_utils.resolve_path(raw)

    def _is_within_roots(self, path: str) -> bool:
        """Handle is within roots."""
        if not self.roots:
            return False
        for root in self.roots:
            if path_utils.is_relative_to(path, root):
                return True
        return False

    def _relative_to_root(self, path: str) -> str:
        """Handle relative to root."""
        for root in self.roots:
            try:
                return path_utils.relative_to(path, root)
            except ValueError:
                continue
        return path

    @staticmethod
    def _matches_root_glob(path: str, pattern: str) -> bool:
        """Allow recursive allow-globs to match the scoped root itself."""
        posix = path_utils.to_posix(path) if path else ""
        if posix not in {".", ""}:
            return False
        normalized = pattern.strip().lstrip("./").rstrip("/")
        return normalized in {"*", "**", "**/*"}

    @staticmethod
    def _matches_globs(path: str, globs: List[str]) -> bool:
        """Handle matches globs."""
        if not globs:
            return False
        for pattern in globs:
            if ScopePolicy._matches_root_glob(path, pattern):
                return True
            if path_utils.match_glob(path, pattern):
                return True
            if pattern.startswith("**/") and path_utils.match_glob(path, pattern[3:]):
                return True
        return False

    def check(self, path: str, *, operation: str = "read") -> ScopeDecision:
        """Execute check."""
        resolved = self.normalize(str(path))
        if not self._is_within_roots(resolved):
            return ScopeDecision(False, "outside_roots")

        rel_path = self._relative_to_root(resolved)
        if self._matches_globs(rel_path, self.deny_globs):
            return ScopeDecision(False, "denied_glob")
        if self.allow_globs and not self._matches_globs(rel_path, self.allow_globs):
            return ScopeDecision(False, "not_in_allowlist")

        ext = path_utils.suffix(resolved).lower()
        if self.allowed_exts and ext not in self.allowed_exts:
            return ScopeDecision(False, "extension_not_allowed")

        mutating_ops = {"write", "delete", "move", "copy", "edit"}
        if operation in mutating_ops and ext in self.read_only_exts:
            return ScopeDecision(False, "extension_read_only")

        return ScopeDecision(True, "allowed")

    def require(self, path: str, *, operation: str = "read") -> None:
        """Execute require."""
        decision = self.check(str(path), operation=operation)
        if not decision.allowed:
            raise PermissionError(f"Scope denied: {decision.reason}")


class PosixScopePolicy:
    """
    Scope enforcement for non-local storage backends.

    Paths are treated as logical POSIX paths (e.g. `/docs/a.txt`) rather than
    OS filesystem paths. Roots are treated as prefix roots.
    """

    def __init__(
        self,
        *,
        roots: Iterable[str],
        allow_globs: Iterable[str] | None = None,
        deny_globs: Iterable[str] | None = None,
        allowed_exts: Iterable[str] | None = None,
        read_only_exts: Iterable[str] | None = None,
    ) -> None:
        """Initialise the instance state."""
        self.roots = [path_utils.posix_path(str(root) if root else "/") for root in roots]
        self.allow_globs = list(allow_globs or ["**/*"])
        self.deny_globs = list(deny_globs or [])
        self.allowed_exts = [ext.lower() for ext in (allowed_exts or [])]
        self.read_only_exts = [ext.lower() for ext in (read_only_exts or [])]

    @staticmethod
    def normalize(path: str) -> str:
        """Execute normalize."""
        return path_utils.posix_path(path if path else "/")

    def _is_within_roots(self, path: str) -> bool:
        """Handle is within roots."""
        if not self.roots:
            return False
        for root in self.roots:
            if root == "/":
                return True
            if path_utils.is_relative_to(path, root):
                return True
        return False

    def _relative_to_root(self, path: str) -> str:
        """Handle relative to root."""
        for root in self.roots:
            try:
                return path_utils.relative_to(path, root)
            except ValueError:
                continue
        return path

    @staticmethod
    def _matches_root_glob(path: str, pattern: str) -> bool:
        """Allow recursive allow-globs to match the scoped root itself."""
        if path not in {".", "", "/"}:
            return False
        normalized = pattern.strip().lstrip("./").rstrip("/")
        return normalized in {"*", "**", "**/*"}

    @staticmethod
    def _matches_globs(path: str, globs: List[str]) -> bool:
        """Handle matches globs."""
        if not globs:
            return False
        for pattern in globs:
            if PosixScopePolicy._matches_root_glob(path, pattern):
                return True
            if path_utils.match_glob(path, pattern):
                return True
            if pattern.startswith("**/") and path_utils.match_glob(path, pattern[3:]):
                return True
        return False

    def check(self, path: str, *, operation: str = "read") -> ScopeDecision:
        """Execute check."""
        resolved = self.normalize(path)
        if not self._is_within_roots(resolved):
            return ScopeDecision(False, "outside_roots")

        rel_path = self._relative_to_root(resolved)
        if self._matches_globs(rel_path, self.deny_globs):
            return ScopeDecision(False, "denied_glob")
        if self.allow_globs and not self._matches_globs(rel_path, self.allow_globs):
            return ScopeDecision(False, "not_in_allowlist")

        ext = path_utils.suffix(resolved).lower()
        if self.allowed_exts and ext not in self.allowed_exts:
            return ScopeDecision(False, "extension_not_allowed")

        mutating_ops = {"write", "delete", "move", "copy", "edit"}
        if operation in mutating_ops and ext in self.read_only_exts:
            return ScopeDecision(False, "extension_read_only")

        return ScopeDecision(True, "allowed")

    def require(self, path: str, *, operation: str = "read") -> None:
        """Execute require."""
        decision = self.check(path, operation=operation)
        if not decision.allowed:
            raise PermissionError(f"Scope denied: {decision.reason}")
