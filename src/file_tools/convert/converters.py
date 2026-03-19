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

"""Conversion helpers and registry.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Conversion registry and file conversion entry point with limit enforcement.
Requirements: NF1.2, CS1.5
Tasks: T18
Architecture: 7.2 Performance
Tests: ST1.7
Recent Change History:
- 2026-02-05: Added size and timeout limit enforcement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from ..limits import enforce_max_file_size, enforce_timeout


class ConversionError(RuntimeError):
    """Raised when conversion fails or no backend is available."""


class BackendNotFoundError(ConversionError):
    """Raised when a requested backend is unknown."""


class BackendUnavailableError(ConversionError):
    """Raised when a requested backend exists but is unavailable."""


class BackendCannotHandleError(ConversionError):
    """Raised when a requested backend cannot handle input/target."""


@dataclass(frozen=True)
class ConversionResult:
    output_path: Optional[Path] = None
    content: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    backend: Optional[str] = None


class ConverterBackend(ABC):
    name = "backend"

    @abstractmethod
    def can_handle(self, input_path: Path, target_format: str) -> bool:
        """Return whether handle is supported."""
        return False

    def is_available(self) -> bool:
        """Return whether available."""
        return True

    @abstractmethod
    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        """Execute convert."""
        raise ConversionError("convert not implemented for backend")


class ConverterRegistry:
    def __init__(self, backends: Optional[Iterable[ConverterBackend]] = None) -> None:
        """Initialise the instance state."""
        self.backends: List[ConverterBackend] = list(backends or [])

    def register(self, backend: ConverterBackend) -> None:
        """Execute register."""
        self.backends.append(backend)

    def get(self, name: str) -> Optional[ConverterBackend]:
        """Execute get."""
        for backend in self.backends:
            if backend.name == name:
                return backend
        return None

    def select(
        self, input_path: Path, target_format: str
    ) -> Optional[ConverterBackend]:
        """Execute select."""
        for backend in self.backends:
            if backend.is_available() and backend.can_handle(input_path, target_format):
                return backend
        return None


def default_registry() -> ConverterRegistry:
    """Execute default registry."""
    from .backends.libreoffice import LibreOfficeBackend
    from .backends.pandoc import PandocBackend
    from .backends.pdf import PdfBackend

    return ConverterRegistry([PandocBackend(), LibreOfficeBackend(), PdfBackend()])


def convert_file(
    input_path: Path,
    target_format: str,
    *,
    output_path: Optional[Path] = None,
    registry: Optional[ConverterRegistry] = None,
    max_input_mb: Optional[int] = None,
    timeout_s: Optional[int] = None,
    preferred_backend: Optional[str] = None,
) -> ConversionResult:
    """Convert file."""
    registry = registry or default_registry()
    enforce_max_file_size(input_path, max_input_mb)
    if preferred_backend:
        backend = registry.get(preferred_backend)
        if backend is None:
            raise BackendNotFoundError(
                f"Unknown conversion backend: {preferred_backend}"
            )
        if not backend.is_available():
            raise BackendUnavailableError(
                f"Requested backend unavailable: {preferred_backend}"
            )
        if not backend.can_handle(input_path, target_format):
            raise BackendCannotHandleError(
                f"Requested backend cannot handle input/target: {preferred_backend}"
            )
    else:
        backend = registry.select(input_path, target_format)
        if backend is None:
            raise ConversionError("No available backend for conversion")
    with enforce_timeout(timeout_s):
        result = backend.convert(input_path, target_format, output_path=output_path)
    return ConversionResult(
        output_path=result.output_path,
        content=result.content,
        warnings=result.warnings,
        backend=backend.name,
    )
