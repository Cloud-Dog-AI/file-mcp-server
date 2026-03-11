"""
file-mcp-server — file_tools/convert/backends/pandoc.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for convert backends pandoc.py.
"""

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import run
from typing import Optional

from ..converters import ConversionError, ConversionResult, ConverterBackend


class PandocBackend(ConverterBackend):
    name = "pandoc"

    def is_available(self) -> bool:
        """Return whether available."""
        return which("pandoc") is not None

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        """Return whether handle is supported."""
        return input_path.suffix.lower() in {".md", ".txt", ".docx"}

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        """Execute convert."""
        if not self.is_available():
            raise ConversionError("pandoc not available")
        output_path = output_path or input_path.with_suffix(f".{target_format}")
        result = run(
            ["pandoc", str(input_path), "-o", str(output_path)], capture_output=True
        )
        if result.returncode != 0:
            raise ConversionError(result.stderr.decode("utf-8", errors="replace"))
        return ConversionResult(output_path=output_path)
