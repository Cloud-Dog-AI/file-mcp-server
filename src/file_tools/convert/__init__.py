"""Conversion pipeline package (scaffold)."""

from .converters import (
    ConversionError,
    ConversionResult,
    ConverterBackend,
    ConverterRegistry,
    convert_file,
    default_registry,
)

__all__ = [
    "ConversionError",
    "ConversionResult",
    "ConverterBackend",
    "ConverterRegistry",
    "convert_file",
    "default_registry",
]
