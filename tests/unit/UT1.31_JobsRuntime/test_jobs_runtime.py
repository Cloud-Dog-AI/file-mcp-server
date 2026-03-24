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

"""Jobs runtime unit tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Unit tests for cloud_dog_jobs integration lifecycle and backend wiring.
Requirements: FR1.21, FR1.23, NF1.3
Tasks: W28A-277
Architecture: 3. Component Architecture, 7. Dependencies & External Services
Tests: UT1.31
"""

from __future__ import annotations

from pathlib import Path

from tests.config_helpers import build_profile
from file_mcp_server.jobs_runtime import FileMcpJobsRuntime


def _profile_with_jobs(tmp_path: Path, *, backend: str) -> object:
    defaults_yaml = """
profiles:
  default:
    server_id: "${FILE_MCP_SERVER_ID}"
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
    scope:
      roots:
        - "${FILE_MCP_ROOT}"
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
      backend: "${FILE_MCP_JOBS_BACKEND}"
      queue_name: "${FILE_MCP_JOBS_QUEUE}"
      payload_max_bytes: "${FILE_MCP_JOBS_PAYLOAD_MAX_BYTES}"
      sql_url: "${FILE_MCP_JOBS_SQL_URL:sqlite:///database/file_mcp.db}"
""".lstrip()
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": "secret",
        "FILE_MCP_ROOT": str(tmp_path),
        "FILE_MCP_SERVER_ID": "ut-file-mcp-server-1",
        "FILE_MCP_JOBS_BACKEND": backend,
        "FILE_MCP_JOBS_QUEUE": "file-mcp-unit",
        "FILE_MCP_JOBS_PAYLOAD_MAX_BYTES": "65536",
        "FILE_MCP_JOBS_SQL_URL": "",
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )


def test_jobs_runtime_memory_lifecycle(tmp_path: Path) -> None:
    profile = _profile_with_jobs(tmp_path, backend="memory")
    runtime = FileMcpJobsRuntime.from_profile(
        profile,
        profile_name="default",
        fallback_sql_url=None,
    )
    assert runtime is not None
    assert runtime.backend_name == "memory"
    assert runtime.server_id == "ut-file-mcp-server-1"

    job_id = runtime.submit_job(
        job_type="file.convert",
        payload={"path": str(tmp_path / "doc.txt"), "target_format": "md"},
        session_id="sess-1",
    )
    assert runtime.mark_running(job_id) is True
    assert runtime.mark_succeeded(job_id) is True

    payload = runtime.get_job(job_id)
    assert payload is not None
    assert payload["job_id"] == job_id
    assert payload["status"] == "succeeded"
    assert payload["session_id"] == "sess-1"

    listed = runtime.list_jobs(limit=10, status="succeeded")
    assert listed
    assert listed[0]["job_id"] == job_id
    assert runtime.queue_status().get("succeeded", 0) >= 1


def test_jobs_runtime_sql_backend_uses_fallback_db_url(tmp_path: Path) -> None:
    profile = _profile_with_jobs(tmp_path, backend="sql")
    sql_url = f"sqlite:///{tmp_path / 'jobs_runtime.db'}"
    runtime = FileMcpJobsRuntime.from_profile(
        profile,
        profile_name="default",
        fallback_sql_url=sql_url,
    )
    assert runtime is not None
    assert runtime.backend_name == "sql"

    job_id = runtime.submit_job(
        job_type="file.upload.b64_decode",
        payload={"path": str(tmp_path / "bin.dat"), "bytes_in": 4},
    )
    assert runtime.mark_running(job_id) is True
    assert runtime.mark_failed(job_id, error="unit failure") is True

    payload = runtime.get_job(job_id)
    assert payload is not None
    assert payload["status"] == "failed"
    assert runtime.queue_status().get("failed", 0) >= 1
    runtime.close()
