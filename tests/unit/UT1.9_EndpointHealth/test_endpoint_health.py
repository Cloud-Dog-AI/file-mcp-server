"""Endpoint health manager tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for startup checks, classification, and recovery logic.
Requirements: FR2.4, NF1.8
Tasks: T22
Architecture: 6. Runtime Health
Tests: UT1.28
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import requests

from file_mcp_server.endpoint_health import EndpointHealthManager
from file_tools.config.models import ProfileConfig


def _profile(root: Path) -> ProfileConfig:
    return ProfileConfig(
        storage={"backend": "local"},
        scope={"roots": [str(root)]},
        endpoint_health={
            "enabled": "true",
            "check_on_startup": "true",
            "check_all_configured_backends": "false",
            "max_retries": "1",
            "retry_interval_s": "0",
            "retry_window_s": "10",
            "max_failures_before_restart": "2",
            "recover_after_s": "0",
        },
    )


def test_run_startup_checks_marks_local_healthy(tmp_path: Path) -> None:
    manager = EndpointHealthManager()
    profile = _profile(tmp_path)
    manager.run_startup_checks(profile_name="default", profile=profile, logger=None)
    state = manager.get_state("default", "local")
    assert state is not None
    assert state.status == "healthy"
    assert state.reason == "startup_probe_ok"
    assert state.requires_restart is False


def test_classify_http_error_503_as_busy_temporary() -> None:
    manager = EndpointHealthManager()
    response = requests.Response()
    response.status_code = 503
    error = requests.HTTPError("service unavailable", response=response)
    assert manager.classify_exception(error) == "busy_temporary"


def test_recover_backend_after_failure(tmp_path: Path) -> None:
    manager = EndpointHealthManager()
    profile = _profile(tmp_path)

    def failing_probe(*_args, **_kwargs) -> None:
        raise TimeoutError("probe timeout")

    manager._probe_backend = failing_probe  # type: ignore[method-assign]
    manager.run_startup_checks(profile_name="default", profile=profile, logger=None)
    failed = manager.get_state("default", "local")
    assert failed is not None
    assert failed.status in {"temporary_unavailable", "busy_temporary", "failed"}

    manager._probe_backend = lambda *_args, **_kwargs: None  # type: ignore[assignment]
    manager._set_state("default", replace(failed, updated_at="2000-01-01T00:00:00+00:00"))
    recovered = manager.maybe_recover_backend(
        profile_name="default",
        profile=profile,
        backend_name="local",
        logger=None,
    )
    assert recovered is not None
    assert recovered.status == "healthy"
    assert recovered.reason == "recovered"


def test_configured_backends_ignores_unresolved_placeholders(tmp_path: Path) -> None:
    manager = EndpointHealthManager()
    profile = ProfileConfig(
        storage={
            "backend": "local",
            "s3": {"endpoint": "${FILE_MCP_S3_ENDPOINT}"},
            "webdav": {"base_url": "${FILE_MCP_WEBDAV_BASE_URL}"},
            "ftp": {"host": "${FILE_MCP_FTP_HOST}"},
            "google_drive": {"folder_id": "${FILE_MCP_GDRIVE_FOLDER_ID}"},
        },
        scope={"roots": [str(tmp_path)]},
    )
    assert manager._configured_backends(profile) == ["local"]
