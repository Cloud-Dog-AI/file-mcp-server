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

"""Conversion pipeline tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for conversion registry and limit enforcement.
Requirements: FR1.21, NF1.2, CS1.5
Tasks: T13, T18
Architecture: 6.9 Conversion, 7.2 Performance
Tests: UT1.16, ST1.7
Recent Change History:
- 2026-02-05: Added limit enforcement coverage.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from tests.config_helpers import build_profile
from file_tools.convert import (
    ConversionError,
    ConverterBackend,
    ConverterRegistry,
    convert_file,
)
from file_tools.convert.converters import ConversionResult
from file_tools.limits import LimitError


class DummyBackend(ConverterBackend):
    name = "dummy"

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        return True

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Path | None = None,
    ) -> ConversionResult:
        return ConversionResult(content="ok")


class SlowBackend(ConverterBackend):
    name = "slow"

    def __init__(self, *, sleep_s: float) -> None:
        self._sleep_s = sleep_s

    def can_handle(self, input_path: Path, target_format: str) -> bool:
        return True

    def convert(
        self,
        input_path: Path,
        target_format: str,
        *,
        output_path: Path | None = None,
    ) -> ConversionResult:
        time.sleep(self._sleep_s)
        return ConversionResult(content="slow")


def _build_profile(tmp_path: Path, *, max_input_mb: int, timeout_s: int):
    defaults_yaml = """
profiles:
  default:
    conversion:
      max_input_mb: "${FILE_MCP_CONVERSION_MAX_INPUT_MB}"
    limits:
      conversion_timeout_s: "${FILE_MCP_CONVERSION_TIMEOUT_S}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_CONVERSION_MAX_INPUT_MB": str(max_input_mb),
        "FILE_MCP_CONVERSION_TIMEOUT_S": str(timeout_s),
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_convert_file_with_dummy_backend(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path, max_input_mb=10, timeout_s=2)
    registry = ConverterRegistry([DummyBackend()])
    input_path = tmp_path / "input.txt"
    input_path.write_text("data")

    result = convert_file(
        input_path,
        "txt",
        registry=registry,
        max_input_mb=profile.conversion.max_input_mb,
        timeout_s=profile.limits.conversion_timeout_s,
    )
    assert result.content == "ok"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_convert_file_no_backend(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path, max_input_mb=10, timeout_s=2)
    registry = ConverterRegistry([])
    input_path = tmp_path / "input.txt"
    input_path.write_text("data")

    with pytest.raises(ConversionError):
        convert_file(
            input_path,
            "txt",
            registry=registry,
            max_input_mb=profile.conversion.max_input_mb,
            timeout_s=profile.limits.conversion_timeout_s,
        )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_convert_file_max_input_mb(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path, max_input_mb=1, timeout_s=2)
    registry = ConverterRegistry([DummyBackend()])
    input_path = tmp_path / "input.txt"
    max_mb = profile.conversion.max_input_mb or 1
    input_path.write_text("data" + ("x" * (max_mb * 1024 * 1024 + 1)))

    with pytest.raises(LimitError):
        convert_file(
            input_path,
            "txt",
            registry=registry,
            max_input_mb=profile.conversion.max_input_mb,
            timeout_s=profile.limits.conversion_timeout_s,
        )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_convert_file_timeout(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.fail("Timeout enforcement uses POSIX signals")
    profile = _build_profile(tmp_path, max_input_mb=10, timeout_s=1)
    timeout_s = profile.limits.conversion_timeout_s or 1
    registry = ConverterRegistry([SlowBackend(sleep_s=timeout_s + 1)])
    input_path = tmp_path / "input.txt"
    input_path.write_text("data")

    with pytest.raises(TimeoutError):
        convert_file(
            input_path,
            "txt",
            registry=registry,
            max_input_mb=profile.conversion.max_input_mb,
            timeout_s=timeout_s,
        )
