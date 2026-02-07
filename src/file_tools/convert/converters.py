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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from ..limits import enforce_max_file_size, enforce_timeout


class ConversionError(RuntimeError):
    """Raised when conversion fails or no backend is available."""


@dataclass(frozen=True)
class ConversionResult:
    output_path: Optional[Path] = None
    content: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ConverterBackend:
    name = "backend"

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        raise NotImplementedError


class ConverterRegistry:
    def __init__(self, backends: Optional[Iterable[ConverterBackend]] = None) -> None:
        self.backends: List[ConverterBackend] = list(backends or [])

    def register(self, backend: ConverterBackend) -> None:
        self.backends.append(backend)

    def select(self, input_path: Path, target_format: str) -> Optional[ConverterBackend]:
        for backend in self.backends:
            if backend.is_available() and backend.can_handle(input_path, target_format):
                return backend
        return None


def default_registry() -> ConverterRegistry:
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
) -> ConversionResult:
    registry = registry or default_registry()
    enforce_max_file_size(input_path, max_input_mb)
    backend = registry.select(input_path, target_format)
    if backend is None:
        raise ConversionError("No available backend for conversion")
    with enforce_timeout(timeout_s):
        return backend.convert(input_path, target_format, output_path=output_path)
