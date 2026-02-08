"""Conversion pipeline package (scaffold)."""

from .converters import (
    BackendCannotHandleError,
    BackendNotFoundError,
    BackendUnavailableError,
    ConversionError,
    ConversionResult,
    ConverterBackend,
    ConverterRegistry,
    convert_file,
    default_registry,
)

__all__ = [
    "ConversionError",
    "BackendNotFoundError",
    "BackendUnavailableError",
    "BackendCannotHandleError",
    "ConversionResult",
    "ConverterBackend",
    "ConverterRegistry",
    "convert_file",
    "default_registry",
]
