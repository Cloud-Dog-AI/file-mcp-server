from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

# Base runtime env (non-secret defaults) tracked in repo.
_DEFAULT_BASE_ENV = Path("run/env.remote-storage.base")
# External secret file generated during migration; not tracked in repo.
_DEFAULT_SECRETS_ENV = Path("/opt/iac/Development/cloud-dog-ai/env-file-mcp-server-secrets")
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
    override = os.getenv("FILE_MCP_REMOTE_BASE_ENV_PATH", "").strip()
    if override:
        return _resolve_path(override, repo_root)
    return repo_root / _DEFAULT_BASE_ENV


def remote_secrets_env_path(repo_root: Path) -> Path:
    override = os.getenv("FILE_MCP_REMOTE_SECRETS_ENV_PATH", "").strip()
    if override:
        return _resolve_path(override, repo_root)
    return _DEFAULT_SECRETS_ENV


def merged_remote_env(repo_root: Path, *, include_google: bool = False) -> dict[str, str]:
    merged: dict[str, str] = {}

    base_env = remote_base_env_path(repo_root)
    if base_env.exists():
        merged.update(parse_env_file(base_env))

    secrets_env = remote_secrets_env_path(repo_root)
    if secrets_env.exists():
        merged.update(parse_env_file(secrets_env))

    if include_google:
        google_env = repo_root / _DEFAULT_GOOGLE_ENV
        if google_env.exists():
            merged.update(parse_env_file(google_env))

    merged.update(dict(os.environ))
    return merged


def file_mcp_env_values(env: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in env.items():
        if key.startswith("FILE_MCP_") or key in {"REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SSL_CERT_DIR"}:
            out[key] = value
    return out


def write_env_file(path: Path, env: Mapping[str, str]) -> None:
    lines: list[str] = []
    for key in sorted(env.keys()):
        value = str(env[key]).replace("\n", "")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
