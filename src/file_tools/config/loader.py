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


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
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


def _load_env_files(env_files: Iterable[Path]) -> None:
    merged: Dict[str, str] = {}
    for env_file in env_files:
        if not env_file.exists():
            continue
        values = dotenv_values(env_file)
        for key, value in values.items():
            if value is None:
                continue
            merged[key] = value
    for key, value in merged.items():
        if key not in os.environ:
            os.environ[key] = value


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
    _load_env_files(env_files)

    merged = _deep_merge(_load_yaml(defaults_file), _load_yaml(config_file))
    expanded = _expand_env(merged)
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
