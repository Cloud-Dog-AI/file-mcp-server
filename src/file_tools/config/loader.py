"""file_tools config loader.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Load configuration with env/YAML precedence and profile selection.
Requirements: NF1.7
Tasks: T18
Architecture: 3.3 Example schema
Tests: UT1.1
Recent Change History:
- 2026-02-05: Added multi-env loading with left-to-right precedence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Union
import re

import os

import yaml
from dotenv import dotenv_values

from .models import ProfileConfig, ServerConfig


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any, *, environment: Dict[str, str]) -> Any:
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return environment.get(key, match.group(0))

        return _VAR_PATTERN.sub(_replace, value)
    if isinstance(value, list):
        return [_expand_env(item, environment=environment) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item, environment=environment) for key, item in value.items()}
    return value


EnvPath = Union[str, Path, Sequence[Union[str, Path]]]


def _normalize_env_paths(root: Path, env_path: Optional[EnvPath]) -> Iterable[Path]:
    if env_path is None:
        return [root / ".env"]
    if isinstance(env_path, Path):
        return [env_path]
    if isinstance(env_path, str):
        parts = [part.strip() for part in env_path.split(",") if part.strip()]
        return [Path(part) for part in parts]
    return [Path(item) for item in env_path]


def _load_env_files(env_files: Iterable[Path]) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for env_file in env_files:
        if not env_file.exists():
            continue
        values = dotenv_values(env_file)
        for key, value in values.items():
            if value is None:
                continue
            merged[key] = value
    return merged


def _extract_var_paths(value: Any, *, path: tuple[Any, ...] = ()) -> Dict[str, list[tuple[Any, ...]]]:
    out: Dict[str, list[tuple[Any, ...]]] = {}
    if isinstance(value, str):
        match = _VAR_PATTERN.fullmatch(value.strip())
        if match:
            out[match.group(1)] = [path]
        return out
    if isinstance(value, list):
        for idx, item in enumerate(value):
            child = _extract_var_paths(item, path=path + (idx,))
            for key, paths in child.items():
                out.setdefault(key, []).extend(paths)
        return out
    if isinstance(value, dict):
        for key, item in value.items():
            child = _extract_var_paths(item, path=path + (key,))
            for child_key, paths in child.items():
                out.setdefault(child_key, []).extend(paths)
        return out
    return out


def _set_at_path(root: Any, path: tuple[Any, ...], value: Any) -> None:
    current = root
    for segment in path[:-1]:
        if isinstance(segment, int):
            if not isinstance(current, list) or segment >= len(current):
                return
            current = current[segment]
            continue
        if not isinstance(current, dict) or segment not in current:
            return
        current = current[segment]
    leaf = path[-1]
    if isinstance(leaf, int):
        if isinstance(current, list) and leaf < len(current):
            current[leaf] = value
        return
    if isinstance(current, dict):
        current[leaf] = value


def _apply_env_overrides(
    *,
    merged: Dict[str, Any],
    defaults_data: Dict[str, Any],
    config_data: Dict[str, Any],
    environment: Dict[str, str],
) -> Dict[str, Any]:
    var_paths: Dict[str, list[tuple[Any, ...]]] = {}
    for source in (defaults_data, config_data):
        discovered = _extract_var_paths(source)
        for key, paths in discovered.items():
            var_paths.setdefault(key, []).extend(paths)

    deduped: Dict[str, list[tuple[Any, ...]]] = {}
    for key, paths in var_paths.items():
        seen: set[tuple[Any, ...]] = set()
        ordered: list[tuple[Any, ...]] = []
        for item in paths:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        deduped[key] = ordered

    for env_key, env_value in environment.items():
        for path in deduped.get(env_key, []):
            _set_at_path(merged, path, env_value)

    return merged


def load_config(
    *,
    root_dir: Optional[str] = None,
    env_path: Optional[EnvPath] = None,
    config_path: Optional[str] = None,
    defaults_path: Optional[str] = None,
) -> ServerConfig:
    root = Path(root_dir).resolve() if root_dir else Path.cwd()
    config_file = Path(config_path) if config_path else root / "config.yaml"
    defaults_file = Path(defaults_path) if defaults_path else root / "defaults.yaml"

    env_files = _normalize_env_paths(root, env_path)
    env_file_values = _load_env_files(env_files)
    effective_env: Dict[str, str] = dict(env_file_values)
    effective_env.update(dict(os.environ))

    defaults_data = _load_yaml(defaults_file)
    config_data = _load_yaml(config_file)
    merged = _deep_merge(defaults_data, config_data)
    merged = _apply_env_overrides(
        merged=merged,
        defaults_data=defaults_data,
        config_data=config_data,
        environment=effective_env,
    )
    expanded = _expand_env(merged, environment=effective_env)
    return ServerConfig.model_validate(expanded)


def get_profile(
    config: ServerConfig,
    name: Optional[str] = None,
    *,
    default_profile: str = "default",
) -> ProfileConfig:
    profile_name = name or default_profile
    try:
        return config.profiles[profile_name]
    except KeyError as exc:
        raise KeyError(f"Unknown profile: {profile_name}") from exc
