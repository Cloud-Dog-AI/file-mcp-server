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

from __future__ import annotations

from tests.env_runtime import env_get, runtime_env

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Mapping

import yaml

from cloud_dog_config import load_config as platform_load  # type: ignore[import-untyped]
from cloud_dog_config.vault.client import (  # type: ignore[import-untyped]
    VaultClient,
    VaultConnectionConfig,
)

# Base runtime env (non-secret defaults) tracked in repo.
_DEFAULT_BASE_ENV = Path("run/env.remote-storage.base")
# Remote credential env source is now repo-local and Vault-expression based.
_DEFAULT_SECRETS_ENV = Path("private/env-remote-storage")
_DEFAULT_GOOGLE_ENV = Path("private/env-google-drive")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _resolve_path(raw: str, repo_root: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def remote_base_env_path(repo_root: Path) -> Path:
    override = env_get("FILE_MCP_REMOTE_BASE_ENV_PATH", "").strip()
    if override:
        return _resolve_path(override, repo_root)
    return repo_root / _DEFAULT_BASE_ENV


def remote_secrets_env_path(repo_root: Path) -> Path:
    override = env_get("FILE_MCP_REMOTE_SECRETS_ENV_PATH", "").strip()
    if override:
        return _resolve_path(override, repo_root)
    return repo_root / _DEFAULT_SECRETS_ENV


def _coerce_env_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return str(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.startswith("${") and candidate.endswith("}"):
            return None
        return candidate
    if isinstance(value, (list, tuple)):
        # Most env values in this project are scalars; only keep scalar lists where expected.
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ",".join(parts) if parts else None
    return None


def _is_unresolved_env_value(value: str | None) -> bool:
    if value is None:
        return True
    candidate = value.strip()
    if not candidate:
        return True
    return candidate.startswith("${") and candidate.endswith("}")


def _pick_first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


@contextmanager
def _temporary_env(values: Mapping[str, str]):
    original = dict(runtime_env)
    try:
        for key, value in values.items():
            runtime_env[key] = value
        yield
    finally:
        runtime_env.clear()
        runtime_env.update(original)


def _resolve_vault_backed_remote_values(
    repo_root: Path,
    *,
    env_files: list[str],
) -> dict[str, str]:
    if not env_get("VAULT_ADDR") or not env_get("VAULT_TOKEN"):
        override = env_get("FILE_MCP_VAULT_ENV_PATH", "").strip()
        candidates: list[Path] = []
        if override:
            candidates.append(_resolve_path(override, repo_root))
        candidates.extend(
            [
                repo_root / "private/env-vault",
                repo_root.parent / "env-vault-admin",
                repo_root.parent / "env-vault",
                repo_root.parent / "cloud-dog-ai-private/private/vault_read.env",
            ]
        )
        existing = [path for path in candidates if path.exists()]
    else:
        existing = []

    # Resolve only keys required by remote storage suites.
    mapping: dict[str, str] = {
        "FILE_MCP_API_KEY_PRIMARY": "profiles.default.auth.api_keys",
        "FILE_MCP_WEBDAV_BASE_URL": "profiles.default.storage.webdav.base_url",
        "FILE_MCP_WEBDAV_USERNAME": "profiles.default.storage.webdav.username",
        "FILE_MCP_WEBDAV_PASSWORD": "profiles.default.storage.webdav.password",
        "FILE_MCP_FTP_HOST": "profiles.default.storage.ftp.host",
        "FILE_MCP_FTP_PORT": "profiles.default.storage.ftp.port",
        "FILE_MCP_FTP_USERNAME": "profiles.default.storage.ftp.username",
        "FILE_MCP_FTP_PASSWORD": "profiles.default.storage.ftp.password",
        "FILE_MCP_S3_ENDPOINT": "profiles.default.storage.s3.endpoint",
        "FILE_MCP_S3_BUCKET": "profiles.default.storage.s3.bucket",
        "FILE_MCP_S3_ACCESS_KEY": "profiles.default.storage.s3.access_key",
        "FILE_MCP_S3_SECRET_KEY": "profiles.default.storage.s3.secret_key",
        "FILE_MCP_GDRIVE_USER_EMAIL": "profiles.default.storage.google_drive.user_email",
        "FILE_MCP_GDRIVE_FOLDER_ID": "profiles.default.storage.google_drive.folder_id",
        "FILE_MCP_GDRIVE_FOLDER_URL": "profiles.default.storage.google_drive.folder_url",
        "FILE_MCP_GDRIVE_CLIENT_ID": "profiles.default.storage.google_drive.client_id",
        "FILE_MCP_GDRIVE_CLIENT_SECRET": "profiles.default.storage.google_drive.client_secret",
        "FILE_MCP_GDRIVE_REFRESH_TOKEN": "profiles.default.storage.google_drive.refresh_token",
        "FILE_MCP_GDRIVE_ACCESS_TOKEN": "profiles.default.storage.google_drive.access_token",
        "FILE_MCP_GDRIVE_REDIRECT_URI": "profiles.default.storage.google_drive.redirect_uri",
        "FILE_MCP_GDRIVE_TOKEN_URI": "profiles.default.storage.google_drive.token_uri",
    }

    remote_required = {
        "FILE_MCP_WEBDAV_BASE_URL",
        "FILE_MCP_WEBDAV_USERNAME",
        "FILE_MCP_WEBDAV_PASSWORD",
        "FILE_MCP_FTP_HOST",
        "FILE_MCP_FTP_USERNAME",
        "FILE_MCP_FTP_PASSWORD",
        "FILE_MCP_S3_ENDPOINT",
        "FILE_MCP_S3_ACCESS_KEY",
        "FILE_MCP_S3_SECRET_KEY",
    }

    def _resolve_with(vault_vars: Mapping[str, str]) -> dict[str, str]:
        with _temporary_env(vault_vars):
            try:
                config = platform_load(
                    env_files=env_files,
                    config_yaml=str(repo_root / "config.yaml"),
                    defaults_yaml=str(repo_root / "defaults.yaml"),
                    unresolved_policy="strict",
                    vault_enabled=True,
                )
            except Exception:
                return {}
        out: dict[str, str] = {}
        for env_key, dotted_path in mapping.items():
            value = config.get(dotted_path)
            if env_key == "FILE_MCP_API_KEY_PRIMARY" and isinstance(
                value, (list, tuple)
            ):
                value = value[0] if value else None
            coerced = _coerce_env_value(value)
            if coerced:
                out[env_key] = coerced
        return out

    attempts: list[dict[str, str]] = []

    # First try current runtime VAULT_* (if already exported by caller).
    if env_get("VAULT_ADDR") and env_get("VAULT_TOKEN"):
        attempts.append(_resolve_with({}))

    # Then try discovered candidate vault env files until remote credentials resolve.
    for selected in existing:
        candidate_vars: dict[str, str] = {}
        for key, value in parse_env_file(selected).items():
            if key.startswith("VAULT_") and value:
                candidate_vars[key] = value
        resolved = _resolve_with(candidate_vars)
        attempts.append(resolved)
        if any(resolved.get(key) for key in remote_required):
            return resolved

    # Fall back to the best effort (first attempt if any), else empty.
    return attempts[0] if attempts else {}


def _read_storage_from_vault_blob(vault_env: Mapping[str, str]) -> dict[str, object]:
    addr = (vault_env.get("VAULT_ADDR") or env_get("VAULT_ADDR", "")).strip()
    token = (vault_env.get("VAULT_TOKEN") or env_get("VAULT_TOKEN", "")).strip()
    mount_raw = (
        (vault_env.get("VAULT_MOUNT_POINT") or env_get("VAULT_MOUNT_POINT", ""))
        .strip()
        .strip("/")
    )
    config_path = (
        (vault_env.get("VAULT_CONFIG_PATH") or env_get("VAULT_CONFIG_PATH", ""))
        .strip()
        .strip("/")
    )
    if not (addr and token and mount_raw):
        return {}

    try:
        client = VaultClient(
            VaultConnectionConfig(
                server=addr,
                token=token,
                timeout_seconds=5.0,
                mount_point=mount_raw,
            )
        )
        raw = client.read(config_path or "config")
    except Exception:
        return {}
    try:
        if isinstance(raw, str):
            raw = json.loads(raw)
    except ValueError:
        return {}

    if not isinstance(raw, dict):
        return {}
    cfg = raw.get("json", raw)
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except ValueError:
            return {}
    if not isinstance(cfg, dict):
        return {}
    if isinstance(cfg.get("dev"), dict):
        cfg = cfg["dev"]
    storage = cfg.get("storage", {})
    return storage if isinstance(storage, dict) else {}


def _resolve_remote_values_from_vault_blob(
    vault_env: Mapping[str, str],
) -> dict[str, str]:
    storage = _read_storage_from_vault_blob(vault_env)
    if not storage:
        return {}

    resolved: dict[str, str] = {}

    webdav = storage.get("webdav", {})
    if isinstance(webdav, dict):
        username = _coerce_env_value(webdav.get("username"))
        password = _coerce_env_value(webdav.get("password"))
        base_url = _coerce_env_value(webdav.get("url"))
        if username:
            resolved["FILE_MCP_WEBDAV_USERNAME"] = username
        if password:
            resolved["FILE_MCP_WEBDAV_PASSWORD"] = password
        if base_url:
            resolved["FILE_MCP_WEBDAV_BASE_URL"] = base_url

    ftp = storage.get("ftp", {})
    if isinstance(ftp, dict):
        username = _coerce_env_value(ftp.get("username"))
        password = _coerce_env_value(ftp.get("password"))
        host = _coerce_env_value(ftp.get("host"))
        port = _coerce_env_value(ftp.get("port"))
        if username:
            resolved["FILE_MCP_FTP_USERNAME"] = username
        if password:
            resolved["FILE_MCP_FTP_PASSWORD"] = password
        if host:
            resolved["FILE_MCP_FTP_HOST"] = host
        if port:
            resolved["FILE_MCP_FTP_PORT"] = port

    s3 = storage.get("s3", {})
    if isinstance(s3, dict):
        access_key = _coerce_env_value(s3.get("access_key_id"))
        secret_key = _coerce_env_value(s3.get("secret_access_key"))
        endpoint = _coerce_env_value(s3.get("endpoint"))
        bucket = _coerce_env_value(s3.get("bucket"))
        region = _coerce_env_value(s3.get("region"))
        if access_key:
            resolved["FILE_MCP_S3_ACCESS_KEY"] = access_key
        if secret_key:
            resolved["FILE_MCP_S3_SECRET_KEY"] = secret_key
        if endpoint:
            resolved["FILE_MCP_S3_ENDPOINT"] = endpoint
        if bucket:
            resolved["FILE_MCP_S3_BUCKET"] = bucket
        if region is not None:
            resolved["FILE_MCP_S3_REGION"] = region

    google_drive = storage.get("google_drive", {})
    if isinstance(google_drive, dict):
        client_id = _coerce_env_value(google_drive.get("client_id"))
        client_secret = _coerce_env_value(google_drive.get("client_secret"))
        if client_id:
            resolved["FILE_MCP_GDRIVE_CLIENT_ID"] = client_id
        if client_secret:
            resolved["FILE_MCP_GDRIVE_CLIENT_SECRET"] = client_secret

    return resolved


def _resolve_google_values_from_profile_config(repo_root: Path) -> dict[str, str]:
    config_path = repo_root / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return {}
    if not isinstance(raw, dict):
        return {}
    profiles = raw.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}

    def _extract(profile_node: object) -> dict[str, str]:
        if not isinstance(profile_node, dict):
            return {}
        storage = profile_node.get("storage", {})
        if not isinstance(storage, dict):
            return {}
        drive = storage.get("google_drive", {})
        if not isinstance(drive, dict):
            return {}

        out: dict[str, str] = {}
        mapping = {
            "client_id": "FILE_MCP_GDRIVE_CLIENT_ID",
            "client_secret": "FILE_MCP_GDRIVE_CLIENT_SECRET",
            "refresh_token": "FILE_MCP_GDRIVE_REFRESH_TOKEN",
            "access_token": "FILE_MCP_GDRIVE_ACCESS_TOKEN",
            "folder_id": "FILE_MCP_GDRIVE_FOLDER_ID",
            "folder_url": "FILE_MCP_GDRIVE_FOLDER_URL",
            "user_email": "FILE_MCP_GDRIVE_USER_EMAIL",
            "redirect_uri": "FILE_MCP_GDRIVE_REDIRECT_URI",
            "token_uri": "FILE_MCP_GDRIVE_TOKEN_URI",
        }
        for source_key, env_key in mapping.items():
            value = _coerce_env_value(drive.get(source_key))
            if value:
                out[env_key] = value
        return out

    def _score(values: Mapping[str, str]) -> int:
        score = 0
        if values.get("FILE_MCP_GDRIVE_CLIENT_ID"):
            score += 1
        if values.get("FILE_MCP_GDRIVE_CLIENT_SECRET"):
            score += 1
        if values.get("FILE_MCP_GDRIVE_FOLDER_ID") or values.get(
            "FILE_MCP_GDRIVE_FOLDER_URL"
        ):
            score += 1
        if values.get("FILE_MCP_GDRIVE_REFRESH_TOKEN") or values.get(
            "FILE_MCP_GDRIVE_ACCESS_TOKEN"
        ):
            score += 1
        return score

    best: dict[str, str] = {}
    best_score = -1

    default_values = _extract(profiles.get("default"))
    default_score = _score(default_values)
    if default_score > best_score:
        best = default_values
        best_score = default_score

    for _, profile in profiles.items():
        values = _extract(profile)
        score = _score(values)
        if score > best_score:
            best = values
            best_score = score
    return best


def merged_remote_env(
    repo_root: Path, *, include_google: bool = False
) -> dict[str, str]:
    merged: dict[str, str] = {}
    env_files: list[str] = []
    google_file_values: dict[str, str] = {}

    base_env = remote_base_env_path(repo_root)
    if base_env.exists():
        env_files.append(str(base_env))
        merged.update(parse_env_file(base_env))

    secrets_env = remote_secrets_env_path(repo_root)
    if secrets_env.exists():
        env_files.append(str(secrets_env))
        merged.update(parse_env_file(secrets_env))

    if include_google:
        google_env = repo_root / _DEFAULT_GOOGLE_ENV
        if google_env.exists():
            env_files.append(str(google_env))
            google_file_values = parse_env_file(google_env)
            merged.update(google_file_values)

    # Resolve vault expressions through the standard package instead of raw text parsing.
    resolved = _resolve_vault_backed_remote_values(repo_root, env_files=env_files)
    merged.update(resolved)
    blob_resolved: dict[str, str] = {}
    profile_google_resolved: dict[str, str] = {}

    if any(
        _is_unresolved_env_value(merged.get(key))
        for key in (
            "FILE_MCP_WEBDAV_USERNAME",
            "FILE_MCP_WEBDAV_PASSWORD",
            "FILE_MCP_FTP_USERNAME",
            "FILE_MCP_FTP_PASSWORD",
            "FILE_MCP_S3_ACCESS_KEY",
            "FILE_MCP_S3_SECRET_KEY",
            "FILE_MCP_GDRIVE_CLIENT_ID",
            "FILE_MCP_GDRIVE_CLIENT_SECRET",
        )
    ):
        candidates = [
            repo_root / "private/env-vault",
            repo_root.parent / "env-vault",
            repo_root.parent / "env-vault-admin",
            repo_root.parent / "cloud-dog-ai-private/private/vault_read.env",
        ]
        selected = _pick_first_existing(candidates)
        if selected is not None:
            blob_resolved = _resolve_remote_values_from_vault_blob(
                parse_env_file(selected)
            )
            merged.update(blob_resolved)
    if include_google:
        profile_google_resolved = _resolve_google_values_from_profile_config(repo_root)
        merged.update(profile_google_resolved)

    os_env = dict(runtime_env)
    merged.update(os_env)

    # If process env injected unresolved `${vault...}` placeholders (e.g. via --env),
    # keep concrete values resolved above.
    for source in (
        resolved,
        blob_resolved,
        profile_google_resolved,
        google_file_values,
    ):
        for key, value in source.items():
            current = merged.get(key)
            if _is_unresolved_env_value(current):
                merged[key] = value

    return merged


def file_mcp_env_values(env: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in env.items():
        if key.startswith("FILE_MCP_") or key in {
            "REQUESTS_CA_BUNDLE",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }:
            out[key] = value
    return out


def write_env_file(path: Path, env: Mapping[str, str]) -> None:
    lines: list[str] = []
    for key in sorted(env.keys()):
        value = str(env[key]).replace("\n", "")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
