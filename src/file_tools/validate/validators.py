# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# """
# License: Apache 2.0
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
file-mcp-server — file_tools/validate/validators.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for validate validators.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import json

from bs4 import BeautifulSoup
from file_tools.adapters import YAMLError
from file_tools.adapters import safe_load as yaml_safe_load
from lxml import etree


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_json(text: str) -> ValidationResult:
    """Validate json."""
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_yaml(text: str) -> ValidationResult:
    """Validate yaml."""
    try:
        yaml_safe_load(text)
    except YAMLError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_xml(text: str) -> ValidationResult:
    """Validate xml."""
    try:
        etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_html(text: str) -> ValidationResult:
    """Validate html."""
    try:
        BeautifulSoup(text, "html.parser")
    except Exception as exc:  # pragma: no cover - defensive
        return ValidationResult(valid=False, errors=[str(exc)])
    return ValidationResult(valid=True)


def validate_markdown(text: str) -> ValidationResult:
    """Validate markdown."""
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
