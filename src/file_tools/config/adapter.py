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

"""file_tools config adapter backed by cloud_dog_config.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Thin adapter from cloud_dog_config GlobalConfig to ServerConfig.
Requirements: NF1.7
Tasks: T18
Architecture: 3.3 Example schema
Tests: UT1.1
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from cloud_dog_config import load_config as _platform_load  # type: ignore[import-untyped]
from cloud_dog_storage import path_utils

from .models import ProfileConfig, ServerConfig

EnvPath = Union[str, Path, Sequence[Union[str, Path]]]


def _normalise_env_paths(root: Path, env_path: Optional[EnvPath]) -> list[str]:
    """Convert env_path argument to a list of existing file path strings."""
    if env_path is None:
        candidate = str(root / ".env")
        return [candidate] if path_utils.exists(candidate) else []
    if isinstance(env_path, (str, Path)):
        parts = (
            str(env_path).split(",") if isinstance(env_path, str) else [str(env_path)]
        )
        return [p.strip() for p in parts if p.strip() and path_utils.exists(p.strip())]
    return [str(p) for p in env_path if path_utils.exists(str(p))]


def _thaw(value: Any) -> Any:
    """Recursively convert frozen mappings/tuples to plain dicts/lists."""
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    return value


def _coerce_auth_api_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure auth api_keys remain strings after platform interpolation."""
    profiles = raw.get("profiles")
    if not isinstance(profiles, dict):
        return raw
    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        auth = profile.get("auth")
        if not isinstance(auth, dict):
            continue
        api_keys = auth.get("api_keys")
        if isinstance(api_keys, list):
            auth["api_keys"] = [str(value) for value in api_keys]
    return raw


def load_config(
    *,
    root_dir: Optional[str] = None,
    env_path: Optional[EnvPath] = None,
    config_path: Optional[str] = None,
    defaults_path: Optional[str] = None,
) -> ServerConfig:
    """Load config through cloud_dog_config and bind to ServerConfig."""
    root = path_utils.as_path(path_utils.resolve_path(root_dir)) if root_dir else path_utils.as_path(path_utils.cwd())
    config_file = config_path if config_path else str(root / "config.yaml")
    defaults_file = defaults_path if defaults_path else str(root / "defaults.yaml")
    env_files = _normalise_env_paths(root, env_path)

    global_config = _platform_load(
        env_files=env_files,
        config_yaml=str(config_file),
        defaults_yaml=str(defaults_file),
        unresolved_policy="strict",
        vault_enabled=True,
    )
    hydrated = _thaw(global_config.data)
    normalised = _coerce_auth_api_keys(hydrated)
    return ServerConfig.model_validate(normalised)


def get_profile(
    config: ServerConfig,
    name: Optional[str] = None,
    *,
    default_profile: str = "default",
) -> ProfileConfig:
    """Return a named profile from the loaded config."""
    profile_name = name or default_profile
    try:
        return config.profiles[profile_name]
    except KeyError as exc:
        raise KeyError(f"Unknown profile: {profile_name}") from exc
