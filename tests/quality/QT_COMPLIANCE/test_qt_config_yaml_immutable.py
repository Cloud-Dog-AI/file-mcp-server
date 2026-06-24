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

"""Static guard for immutable runtime YAML configuration files."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"

CONFIG_CONTEXT_RE = re.compile(
    r"(config|default|defaults)\.ya?ml|\b(active_config|config_path|defaults_path|default_path)\b",
    re.IGNORECASE,
)
WRITER_RE = re.compile(
    r"\b(write_text|write_bytes|writeFile|writeFileSync|safe_dump|yaml\.dump|yaml\.safe_dump)\b"
    r"|\bopen\s*\([^)]*(?:['\"]w['\"]|['\"]a['\"]|['\"]x['\"]|mode\s*=\s*['\"][wax])",
)


def _source_python_files() -> list[Path]:
    return sorted(
        path
        for path in SRC_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and path.is_file()
    )


@pytest.mark.QT
@pytest.mark.mcp
@pytest.mark.req("FR-013")
def test_runtime_source_does_not_write_immutable_config_yaml_files() -> None:
    violations: list[str] = []
    for path in _source_python_files():
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines):
            if not WRITER_RE.search(line):
                continue
            start = max(0, idx - 20)
            end = min(len(lines), idx + 21)
            context = "\n".join(lines[start:end])
            if CONFIG_CONTEXT_RE.search(context):
                violations.append(f"{rel}:{idx + 1}: {line.strip()}")

    assert not violations, (
        "Runtime source must not write config.yaml/default.yaml/defaults.yaml:\n"
        + "\n".join(violations)
    )
