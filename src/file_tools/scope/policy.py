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
from pathlib import Path, PurePosixPath
from typing import Iterable, List
import posixpath


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
        self.roots = [Path(root).resolve() for root in roots]
        self.allow_globs = list(allow_globs or ["**/*"])
        self.deny_globs = list(deny_globs or [])
        self.allowed_exts = [ext.lower() for ext in (allowed_exts or [])]
        self.read_only_exts = [ext.lower() for ext in (read_only_exts or [])]

    def normalize(self, path: str | Path) -> Path:
        """Execute normalize."""
        return Path(path).resolve()

    def _is_within_roots(self, path: Path) -> bool:
        """Handle is within roots."""
        if not self.roots:
            return False
        for root in self.roots:
            try:
                if path.is_relative_to(root):
                    return True
            except AttributeError:
                try:
                    path.relative_to(root)
                except ValueError:
                    continue
                return True
        return False

    def _relative_to_root(self, path: Path) -> Path:
        """Handle relative to root."""
        for root in self.roots:
            try:
                return path.relative_to(root)
            except ValueError:
                continue
        return path

    @staticmethod
    def _matches_globs(path: Path, globs: List[str]) -> bool:
        """Handle matches globs."""
        if not globs:
            return False
        rel_posix = PurePosixPath(path.as_posix())
        for pattern in globs:
            if rel_posix.match(pattern):
                return True
            if pattern.startswith("**/") and rel_posix.match(pattern[3:]):
                return True
        return False

    def check(self, path: str | Path, *, operation: str = "read") -> ScopeDecision:
        """Execute check."""
        resolved = self.normalize(path)
        if not self._is_within_roots(resolved):
            return ScopeDecision(False, "outside_roots")

        rel_path = self._relative_to_root(resolved)
        if self._matches_globs(rel_path, self.deny_globs):
            return ScopeDecision(False, "denied_glob")
        if self.allow_globs and not self._matches_globs(rel_path, self.allow_globs):
            return ScopeDecision(False, "not_in_allowlist")

        ext = resolved.suffix.lower()
        if self.allowed_exts and ext not in self.allowed_exts:
            return ScopeDecision(False, "extension_not_allowed")

        mutating_ops = {"write", "delete", "move", "copy", "edit"}
        if operation in mutating_ops and ext in self.read_only_exts:
            return ScopeDecision(False, "extension_read_only")

        return ScopeDecision(True, "allowed")

    def require(self, path: str | Path, *, operation: str = "read") -> None:
        """Execute require."""
        decision = self.check(path, operation=operation)
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
        self.roots = [PurePosixPath(str(root) if root else "/") for root in roots]
        self.allow_globs = list(allow_globs or ["**/*"])
        self.deny_globs = list(deny_globs or [])
        self.allowed_exts = [ext.lower() for ext in (allowed_exts or [])]
        self.read_only_exts = [ext.lower() for ext in (read_only_exts or [])]

    @staticmethod
    def normalize(path: str) -> PurePosixPath:
        """Execute normalize."""
        p = PurePosixPath(path if path else "/")
        if not str(p).startswith("/"):
            p = PurePosixPath("/") / p
        # PurePosixPath doesn't resolve symlinks; we only normalize `..` parts.
        return PurePosixPath(posixpath.normpath(str(p)))  # type: ignore[name-defined]

    def _is_within_roots(self, path: PurePosixPath) -> bool:
        """Handle is within roots."""
        if not self.roots:
            return False
        for root in self.roots:
            if str(root) == "/":
                return True
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _relative_to_root(self, path: PurePosixPath) -> PurePosixPath:
        """Handle relative to root."""
        for root in self.roots:
            try:
                return path.relative_to(root)
            except ValueError:
                continue
        return path

    @staticmethod
    def _matches_globs(path: PurePosixPath, globs: List[str]) -> bool:
        """Handle matches globs."""
        if not globs:
            return False
        for pattern in globs:
            if path.match(pattern):
                return True
            if pattern.startswith("**/") and path.match(pattern[3:]):
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

        ext = resolved.suffix.lower()
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
