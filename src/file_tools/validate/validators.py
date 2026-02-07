"""Validators scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import json

from bs4 import BeautifulSoup
from lxml import etree
import yaml


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_json(text: str) -> ValidationResult:
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_yaml(text: str) -> ValidationResult:
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_xml(text: str) -> ValidationResult:
    try:
        etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_html(text: str) -> ValidationResult:
    try:
        BeautifulSoup(text, "html.parser")
    except Exception as exc:  # pragma: no cover - defensive
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_markdown(text: str) -> ValidationResult:
    if not text.strip():
        return ValidationResult(valid=True, warnings=["Markdown content is empty"])
    lines = text.splitlines()
    last_level = 0
    for line in lines:
        if line.lstrip().startswith("#"):
            level = len(line.lstrip().split(" ")[0])
            if last_level and level > last_level + 1:
                return ValidationResult(
                    valid=False,
                    errors=["Markdown heading levels skip a level"],
                )
            last_level = level
    return ValidationResult(valid=True)
