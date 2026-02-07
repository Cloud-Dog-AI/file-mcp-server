"""PDF backend scaffolding."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pdfminer.high_level import extract_text

from ..converters import ConversionResult, ConverterBackend


class PdfBackend(ConverterBackend):
    name = "pdf"

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        return input_path.suffix.lower() == ".pdf" and target_format in {"txt", "md"}

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        text = extract_text(str(input_path))
        if output_path:
            output_path.write_text(text, encoding="utf-8")
            return ConversionResult(output_path=output_path)
        return ConversionResult(content=text)
