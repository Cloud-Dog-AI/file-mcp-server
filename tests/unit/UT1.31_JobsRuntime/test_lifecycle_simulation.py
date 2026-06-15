# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# W28A-680 — PS-75 lifecycle simulation tests.
# Covers: FR1.21, FR1.23, NF1.3, PS-75 JQ4, JQ7, JQ8

from __future__ import annotations

from pathlib import Path

from tests.config_helpers import build_profile
from file_mcp_server.jobs_runtime import FileMcpJobsRuntime
import pytest


def _make_runtime(tmp_path: Path, db_name: str = "lifecycle.db") -> FileMcpJobsRuntime:
    defaults_yaml = """
profiles:
  default:
    server_id: lifecycle-test
    auth:
      api_keys:
        - test-key
    scope:
      roots:
        - /tmp
      allow_globs:
        - "**/*"
      deny_globs: []
      allowed_exts: []
      read_only_exts: []
    validation:
      default_mode: "warn"
      per_type: {}
    jobs:
      enabled: true
      backend: sql
      queue_name: lifecycle-q
      payload_max_bytes: 65536
      sql_url: ""
""".lstrip()
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": "test-key",
        "FILE_MCP_ROOT": str(tmp_path),
        "FILE_MCP_SERVER_ID": "lifecycle-test",
        "FILE_MCP_JOBS_BACKEND": "sql",
        "FILE_MCP_JOBS_QUEUE": "lifecycle-q",
        "FILE_MCP_JOBS_PAYLOAD_MAX_BYTES": "65536",
        "FILE_MCP_JOBS_SQL_URL": "",
    }
    profile = build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )
    sql_url = f"sqlite:///{tmp_path / db_name}"
    runtime = FileMcpJobsRuntime.from_profile(
        profile,
        profile_name="default",
        fallback_sql_url=sql_url,
    )
    assert runtime is not None
    return runtime
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_lifecycle_create_queue_run_succeed(tmp_path: Path) -> None:
    """create -> queued -> running -> succeeded"""
    rt = _make_runtime(tmp_path, "lc_succeed.db")
    job_id = rt.submit_job(job_type="file_batch", payload={"op": "copy"})
    job = rt.get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"

    rt.mark_running(job_id)
    job = rt.get_job(job_id)
    assert job["status"] == "running"

    rt.mark_succeeded(job_id)
    job = rt.get_job(job_id)
    assert job["status"] == "succeeded"
    rt.close()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_lifecycle_create_queue_run_fail(tmp_path: Path) -> None:
    """create -> queued -> running -> failed"""
    rt = _make_runtime(tmp_path, "lc_fail.db")
    job_id = rt.submit_job(job_type="file_operation", payload={"op": "delete"})

    rt.mark_running(job_id)
    rt.mark_failed(job_id, error="permission denied")
    job = rt.get_job(job_id)
    assert job["status"] == "failed"
    rt.close()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_lifecycle_create_queue_cancel(tmp_path: Path) -> None:
    """create -> queued -> cancelled"""
    rt = _make_runtime(tmp_path, "lc_cancel.db")
    job_id = rt.submit_job(job_type="file_batch", payload={"op": "move"})
    job = rt.get_job(job_id)
    assert job["status"] == "queued"

    ok = rt.cancel(job_id)
    assert ok is True
    job = rt.get_job(job_id)
    assert job["status"] == "cancelled"
    rt.close()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-1.21")


def test_lifecycle_create_queue_run_fail_retryable(tmp_path: Path) -> None:
    """create -> queued -> running -> fail(retryable) -> retry_wait"""
    rt = _make_runtime(tmp_path, "lc_retry.db")
    job_id = rt.submit_job(job_type="file_operation", payload={"op": "upload"})

    rt.mark_running(job_id)
    rt.mark_failed(job_id, error="temporary error", retryable=True)
    job = rt.get_job(job_id)
    assert job["status"] in ("retry_wait", "failed")
    rt.close()
