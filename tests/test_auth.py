from __future__ import annotations

import pytest

from tests.config_helpers import build_profile
from file_mcp_server.auth import ApiKeyAuth, AuthError, key_fingerprint


def _build_profile(tmp_path, *, primary: str, secondary: str) -> ApiKeyAuth:
    defaults_yaml = """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": primary,
        "FILE_MCP_API_KEY_SECONDARY": secondary,
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )
    return ApiKeyAuth(profile.auth.api_keys)


def test_key_fingerprint_format(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret-key", secondary="")
    fingerprint = key_fingerprint(auth._keys[0])
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) == len("sha256:") + 12


def test_auth_rejects_missing_keys(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="", secondary="")
    with pytest.raises(AuthError, match="No API keys configured"):
        auth.validate("anything")


def test_auth_rejects_missing_token(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    with pytest.raises(AuthError, match="Missing API key"):
        auth.validate(None)


def test_auth_accepts_valid_key(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="other")
    result = auth.validate("secret")
    assert result.ok is True
    assert result.key_fingerprint.startswith("sha256:")


def test_auth_rejects_invalid_key(tmp_path) -> None:
    auth = _build_profile(tmp_path, primary="secret", secondary="")
    with pytest.raises(AuthError, match="Invalid API key"):
        auth.validate("nope")
