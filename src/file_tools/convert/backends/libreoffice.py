"""LibreOffice backend scaffolding."""

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import run
from typing import Optional

from ..converters import ConversionError, ConversionResult, ConverterBackend


class LibreOfficeBackend(ConverterBackend):
    name = "libreoffice"

    def is_available(self) -> bool:
        return which("soffice") is not None

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        return input_path.suffix.lower() in {".docx", ".xlsx", ".pptx"}

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        if not self.is_available():
            raise ConversionError("libreoffice not available")
        output_dir = (output_path.parent if output_path else input_path.parent)
        result = run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                target_format,
                "--outdir",
                str(output_dir),
                str(input_path),
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ConversionError(result.stderr.decode("utf-8", errors="replace"))
        generated = output_dir / f"{input_path.stem}.{target_format}"
        if output_path and output_path != generated:
            generated.replace(output_path)
            generated = output_path
        return ConversionResult(output_path=generated)
