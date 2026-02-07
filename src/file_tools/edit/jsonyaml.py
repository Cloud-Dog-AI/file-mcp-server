"""JSON/YAML edit scaffolding."""

from __future__ import annotations

from typing import Any, List

import json

import yaml


def _parse_pointer(path: str) -> List[str | int]:
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
    if path.startswith("/"):
        return _parse_pointer(path)
    return _parse_dot_path(path)


def _get_value(data: Any, tokens: List[str | int]) -> Any:
    current = data
    for token in tokens:
        current = current[token]
    return current


def _ensure_container(container: Any, token: str | int) -> Any:
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


def json_get(text: str, path: str) -> Any:
    data = json.loads(text)
    return _get_value(data, parse_path(path))


def json_set(text: str, path: str, value: Any) -> str:
    data = json.loads(text)
    updated = _set_value(data, parse_path(path), value)
    return json.dumps(updated, indent=2, ensure_ascii=False)


def json_delete(text: str, path: str) -> str:
    data = json.loads(text)
    updated = _delete_value(data, parse_path(path))
    return json.dumps(updated, indent=2, ensure_ascii=False)


def yaml_get(text: str, path: str) -> Any:
    data = yaml.safe_load(text)
    return _get_value(data, parse_path(path))


def yaml_set(text: str, path: str, value: Any) -> str:
    data = yaml.safe_load(text)
    updated = _set_value(data, parse_path(path), value)
    return yaml.safe_dump(updated, sort_keys=False)


def yaml_delete(text: str, path: str) -> str:
    data = yaml.safe_load(text)
    updated = _delete_value(data, parse_path(path))
    return yaml.safe_dump(updated, sort_keys=False)
