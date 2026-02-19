"""file_tools config adapter backed by cloud_dog_config.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Transitional adapter from cloud_dog_config to ServerConfig models.
Requirements: NF1.7
Tasks: T18
Architecture: 3.3 Example schema
Tests: UT1.1
Recent Change History:
- 2026-02-19: Added adapter for cloud_dog_config migration (PS-80).
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from pathlib import Path
import re
import sys
from typing import Any, Optional, Sequence, Union

import yaml

from .models import ProfileConfig, ServerConfig

EnvPath = Union[str, Path, Sequence[Union[str, Path]]]


def _resolve_platform_modules():
    try:
        module = importlib.import_module("cloud_dog_config")
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[4]
        fallback = (
            repo_root
            / "cloud-dog-ai-platform-standards"
            / "packages"
            / "backend"
            / "platform-config"
        )
        if fallback.exists():
            sys.path.insert(0, str(fallback))
            module = importlib.import_module("cloud_dog_config")
        else:
            raise
    env_parser = importlib.import_module("cloud_dog_config.env_parser")
    loader = importlib.import_module("cloud_dog_config.loader")
    return (
        getattr(module, "load_config"),
        getattr(env_parser, "parse_env_file"),
        getattr(loader, "_select_relevant_os_environ"),
    )


load_platform_config, parse_env_file, select_relevant_os_environ = (
    _resolve_platform_modules()
)


_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _normalize_env_paths(root: Path, env_path: Optional[EnvPath]) -> list[Path]:
    if env_path is None:
        return [root / ".env"]
    if isinstance(env_path, Path):
        return [env_path]
    if isinstance(env_path, str):
        parts = [part.strip() for part in env_path.split(",") if part.strip()]
        return [Path(part) for part in parts]
    return [Path(item) for item in env_path]


def _existing_env_paths(paths: Sequence[Path]) -> list[str]:
    return [str(path) for path in paths if path.exists()]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data


def _extract_var_paths(
    value: Any, *, path: tuple[Any, ...] = ()
) -> dict[str, list[tuple[Any, ...]]]:
    out: dict[str, list[tuple[Any, ...]]] = {}
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


def _build_effective_env(
    *,
    env_files: list[str],
    var_paths: dict[str, list[tuple[Any, ...]]],
) -> dict[str, str]:
    env_file_values: dict[str, str] = {}
    for env_file in env_files:
        parsed = parse_env_file(env_file)
        for key, value in parsed.items():
            env_file_values[key] = value
    base_for_os = {key: "" for key in var_paths}
    os_values = select_relevant_os_environ(base=base_for_os)
    effective_env = dict(env_file_values)
    effective_env.update(os_values)
    return effective_env


def _apply_legacy_env_overrides(
    *,
    compiled: dict[str, Any],
    defaults_data: dict[str, Any],
    config_data: dict[str, Any],
    effective_env: dict[str, str],
) -> dict[str, Any]:
    var_paths: dict[str, list[tuple[Any, ...]]] = {}
    for source in (defaults_data, config_data):
        discovered = _extract_var_paths(source)
        for key, paths in discovered.items():
            var_paths.setdefault(key, []).extend(paths)

    deduped: dict[str, list[tuple[Any, ...]]] = {}
    for key, paths in var_paths.items():
        seen: set[tuple[Any, ...]] = set()
        ordered: list[tuple[Any, ...]] = []
        for item in paths:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        deduped[key] = ordered

    for env_key, env_value in effective_env.items():
        for path in deduped.get(env_key, []):
            _set_at_path(compiled, path, env_value)

    return compiled


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, list):
        return [_thaw(item) for item in value]
    return value


def load_config(
    *,
    root_dir: Optional[str] = None,
    env_path: Optional[EnvPath] = None,
    config_path: Optional[str] = None,
    defaults_path: Optional[str] = None,
) -> ServerConfig:
    """Load config through cloud_dog_config and bind to ServerConfig."""
    root = Path(root_dir).resolve() if root_dir else Path.cwd()
    config_file = Path(config_path) if config_path else root / "config.yaml"
    defaults_file = Path(defaults_path) if defaults_path else root / "defaults.yaml"

    env_files = _existing_env_paths(_normalize_env_paths(root, env_path))
    defaults_data = _load_yaml(defaults_file)
    config_data = _load_yaml(config_file)
    var_paths = _extract_var_paths(defaults_data)
    for key, paths in _extract_var_paths(config_data).items():
        var_paths.setdefault(key, []).extend(paths)
    effective_env = _build_effective_env(env_files=env_files, var_paths=var_paths)

    global_config = load_platform_config(
        env_files=env_files,
        config_yaml=str(config_file),
        defaults_yaml=str(defaults_file),
        unresolved_policy="warn",
        vault_enabled=True,
    )
    compiled = _thaw(global_config.data)
    merged = _apply_legacy_env_overrides(
        compiled=compiled,
        defaults_data=defaults_data,
        config_data=config_data,
        effective_env=effective_env,
    )
    return ServerConfig.model_validate(merged)


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
