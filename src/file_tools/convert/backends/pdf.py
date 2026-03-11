"""
file-mcp-server — file_tools/convert/backends/pdf.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for convert backends pdf.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pdfminer.high_level import extract_text

from ..converters import ConversionResult, ConverterBackend


class PdfBackend(ConverterBackend):
    name = "pdf"

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        """Return whether handle is supported."""
        return input_path.suffix.lower() == ".pdf" and target_format in {"txt", "md"}

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        """Execute convert."""
        text = extract_text(str(input_path))
        if output_path:
            output_path.write_text(text, encoding="utf-8")
            return ConversionResult(output_path=output_path)
        return ConversionResult(content=text)
