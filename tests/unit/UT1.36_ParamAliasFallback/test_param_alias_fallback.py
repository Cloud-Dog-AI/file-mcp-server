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

"""PARAM_ALIASES required-parameter fallback tests.
import pytest

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for alias normalization when alias sources collide with handler parameters.
Requirements: W28A-822, W28A-752
Tasks: T-W28A-822, T-W28A-752
Architecture: 5. Tool Interface
Tests: UT1.36
Recent Change History:
- 2026-06-03: Add required-parameter fallback coverage for alias collisions (W28A-822).
- 2026-06-10: Re-land to canonical main; the W28A-822 fix + test never merged, leaving
  b64_decode_to_file's `data` arg silently stripped (IT1.3/IT1.14 root cause) (W28A-752).
"""

from __future__ import annotations

from typing import Any

from file_tools.tools.schemas import normalize_and_filter_tool_args


def _call(handler: Any, args: dict[str, Any]) -> Any:
    return handler(**normalize_and_filter_tool_args(args, handler))
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_b64_decode_to_file_accepts_path_and_data() -> None:
    def b64_decode_to_file(path: str, data: str) -> dict[str, str]:
        return {"path": path, "data": data}

    result = _call(
        b64_decode_to_file,
        {"path": "/probe.bin", "data": "aGVsbG8="},
    )

    assert result == {"path": "/probe.bin", "data": "aGVsbG8="}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_b64_decode_to_file_accepts_path_and_content() -> None:
    def b64_decode_to_file(path: str, data: str) -> dict[str, str]:
        return {"path": path, "data": data}

    result = _call(
        b64_decode_to_file,
        {"path": "/probe.bin", "content": "aGVsbG8="},
    )

    assert result == {"path": "/probe.bin", "data": "aGVsbG8="}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_admin_create_group_accepts_name_collision_source() -> None:
    def admin_create_group(name: str, description: str = "") -> dict[str, str]:
        return {"name": name, "description": description}

    result = _call(
        admin_create_group,
        {"name": "operators", "description": "Ops team"},
    )

    assert result == {"name": "operators", "description": "Ops team"}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_filepath_alias_to_path_still_works() -> None:
    def read_file(path: str) -> str:
        return path

    result = _call(read_file, {"filepath": "/notes/todo.txt"})

    assert result == "/notes/todo.txt"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.probe  # rtt-2026-06-12 INST3: KEEP-AS-PROBE pending operator REQ-binding


def test_text_alias_to_content_still_works() -> None:
    def write_text(content: str) -> str:
        return content

    result = _call(write_text, {"text": "hello"})

    assert result == "hello"
