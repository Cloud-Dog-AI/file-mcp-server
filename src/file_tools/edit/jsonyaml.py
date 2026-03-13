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
file-mcp-server — file_tools/edit/jsonyaml.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for edit jsonyaml.py.
"""

from __future__ import annotations

from copy import deepcopy
from io import StringIO
from typing import Any, List

import json

from file_tools.adapters import safe_dump as yaml_safe_dump
from file_tools.adapters import safe_load as yaml_safe_load

_RuamelYAMLClass: Any | None
try:
    from ruamel.yaml import YAML as _ImportedRuamelYAML

    _RuamelYAMLClass = _ImportedRuamelYAML
except Exception:  # pragma: no cover - optional dependency guard
    _RuamelYAMLClass = None


_yaml_rt = _RuamelYAMLClass() if _RuamelYAMLClass is not None else None
if _yaml_rt is not None:
    _yaml_rt.preserve_quotes = True


def _parse_pointer(path: str) -> List[str | int]:
    """Handle parse pointer."""
    if path == "" or path == "/":
        return []
    tokens: List[str | int] = []
    for raw in path.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if token.isdigit():
            tokens.append(int(token))
        else:
            tokens.append(token)
    return tokens


def _parse_dot_path(path: str) -> List[str | int]:
    """Handle parse dot path."""
    if path == "":
        return []
    tokens: List[str | int] = []
    buffer: List[str] = []
    idx_buffer: List[str] = []
    in_index = False
    for char in path:
        if char == "." and not in_index:
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            continue
        if char == "[":
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            in_index = True
            idx_buffer = []
            continue
        if char == "]" and in_index:
            if idx_buffer:
                tokens.append(int("".join(idx_buffer)))
            in_index = False
            continue
        if in_index:
            idx_buffer.append(char)
        else:
            buffer.append(char)
    if buffer:
        tokens.append("".join(buffer))
    return tokens


def parse_path(path: str) -> List[str | int]:
    """Parse path."""
    if path.startswith("/"):
        return _parse_pointer(path)
    return _parse_dot_path(path)


def _get_value(data: Any, tokens: List[str | int]) -> Any:
    """Handle get value."""
    current = data
    for token in tokens:
        current = current[token]
    return current


def _ensure_container(container: Any, token: str | int) -> Any:
    """Handle ensure container."""
    if isinstance(token, int):
        if container is None:
            return []
        if not isinstance(container, list):
            raise TypeError("Expected list for index access")
        while len(container) <= token:
            container.append({})
        return container
    if container is None:
        return {}
    if not isinstance(container, dict):
        raise TypeError("Expected dict for key access")
    if token not in container:
        container[token] = {}
    return container


def _set_value(data: Any, tokens: List[str | int], value: Any) -> Any:
    """Handle set value."""
    if not tokens:
        return value
    current = data
    for token in tokens[:-1]:
        current = _ensure_container(current, token)
        current = current[token]
    final = tokens[-1]
    if isinstance(final, int):
        if not isinstance(current, list):
            raise TypeError("Expected list for index access")
        while len(current) <= final:
            current.append(None)
        current[final] = value
    else:
        if not isinstance(current, dict):
            raise TypeError("Expected dict for key access")
        current[final] = value
    return data


def _delete_value(data: Any, tokens: List[str | int]) -> Any:
    """Handle delete value."""
    if not tokens:
        raise ValueError("Cannot delete root")
    current = data
    for token in tokens[:-1]:
        current = current[token]
    final = tokens[-1]
    if isinstance(final, int):
        current.pop(final)
    else:
        current.pop(final, None)
    return data


def _merge_nodes(base: Any, incoming: Any) -> Any:
    """Handle merge nodes."""
    if isinstance(base, dict) and isinstance(incoming, dict):
        merged = dict(base)
        for key, value in incoming.items():
            if key in merged:
                merged[key] = _merge_nodes(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(incoming)


def json_get(text: str, path: str) -> Any:
    """Execute json get."""
    data = json.loads(text)
    return _get_value(data, parse_path(path))


def json_set(text: str, path: str, value: Any) -> str:
    """Execute json set."""
    data = json.loads(text)
    updated = _set_value(data, parse_path(path), value)
    return json.dumps(updated, indent=2, ensure_ascii=False)


def json_delete(text: str, path: str) -> str:
    """Execute json delete."""
    data = json.loads(text)
    updated = _delete_value(data, parse_path(path))
    return json.dumps(updated, indent=2, ensure_ascii=False)


def json_copy(text: str, from_path: str, to_path: str) -> str:
    """Execute json copy."""
    data = json.loads(text)
    value = deepcopy(_get_value(data, parse_path(from_path)))
    updated = _set_value(data, parse_path(to_path), value)
    return json.dumps(updated, indent=2, ensure_ascii=False)


def json_move(text: str, from_path: str, to_path: str) -> str:
    """Execute json move."""
    data = json.loads(text)
    value = deepcopy(_get_value(data, parse_path(from_path)))
    updated = _delete_value(data, parse_path(from_path))
    updated = _set_value(updated, parse_path(to_path), value)
    return json.dumps(updated, indent=2, ensure_ascii=False)


def json_merge(text: str, path: str, value: Any) -> str:
    """Execute json merge."""
    data = json.loads(text)
    tokens = parse_path(path)
    existing = _get_value(data, tokens) if tokens else data
    merged = _merge_nodes(existing, value)
    updated = _set_value(data, tokens, merged) if tokens else merged
    return json.dumps(updated, indent=2, ensure_ascii=False)


def yaml_get(text: str, path: str) -> Any:
    """Execute yaml get."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    return _get_value(data, parse_path(path))


def yaml_set(text: str, path: str, value: Any) -> str:
    """Execute yaml set."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    updated = _set_value(data, parse_path(path), value)
    if _yaml_rt is not None:
        output = StringIO()
        _yaml_rt.dump(updated, output)
        return output.getvalue()
    return yaml_safe_dump(updated, sort_keys=False)


def yaml_delete(text: str, path: str) -> str:
    """Execute yaml delete."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    updated = _delete_value(data, parse_path(path))
    if _yaml_rt is not None:
        output = StringIO()
        _yaml_rt.dump(updated, output)
        return output.getvalue()
    return yaml_safe_dump(updated, sort_keys=False)


def yaml_copy(text: str, from_path: str, to_path: str) -> str:
    """Execute yaml copy."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    value = deepcopy(_get_value(data, parse_path(from_path)))
    updated = _set_value(data, parse_path(to_path), value)
    if _yaml_rt is not None:
        output = StringIO()
        _yaml_rt.dump(updated, output)
        return output.getvalue()
    return yaml_safe_dump(updated, sort_keys=False)


def yaml_move(text: str, from_path: str, to_path: str) -> str:
    """Execute yaml move."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    value = deepcopy(_get_value(data, parse_path(from_path)))
    updated = _delete_value(data, parse_path(from_path))
    updated = _set_value(updated, parse_path(to_path), value)
    if _yaml_rt is not None:
        output = StringIO()
        _yaml_rt.dump(updated, output)
        return output.getvalue()
    return yaml_safe_dump(updated, sort_keys=False)


def yaml_merge(text: str, path: str, value: Any) -> str:
    """Execute yaml merge."""
    if _yaml_rt is not None:
        data = _yaml_rt.load(text)
    else:
        data = yaml_safe_load(text)
    tokens = parse_path(path)
    existing = _get_value(data, tokens) if tokens else data
    merged = _merge_nodes(existing, value)
    updated = _set_value(data, tokens, merged) if tokens else merged
    if _yaml_rt is not None:
        output = StringIO()
        _yaml_rt.dump(updated, output)
        return output.getvalue()
    return yaml_safe_dump(updated, sort_keys=False)
