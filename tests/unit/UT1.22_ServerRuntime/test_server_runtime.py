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

from tests.env_runtime import runtime_env

import asyncio
import json
import re

from tests.config_helpers import build_profile
from file_tools.config.models import HttpServerConfig
from file_mcp_server.jobs_runtime import FileMcpJobsRuntime
from file_mcp_server.server import (
    HealthCheckMiddleware,
    StreamableHttpAcceptCompatibilityMiddleware,
    build_tool_registry,
    resolve_http_settings,
)
from file_mcp_server.server_runtime import (
    _deleted_profile_name,
    _merge_active_db_profiles_into_config,
    _normalise_profile_mapping,
    _resolve_auth_api_key_value,
)
from file_tools.config.models import ProfileConfig, ServerConfig


class _FakeDbRow:
    def __init__(self, *, name: str, config_json: str, is_active: bool = True) -> None:
        self.name = name
        self.config_json = config_json
        self.is_active = is_active


class _FakeQuery:
    def __init__(self, rows: list[_FakeDbRow]) -> None:
        self._rows = rows
        self._filters: dict[str, object] = {}

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def all(self) -> list[_FakeDbRow]:
        rows = self._rows
        if "is_active" in self._filters:
            rows = [row for row in rows if row.is_active == self._filters["is_active"]]
        return rows


class _FakeSession:
    def __init__(self, rows: list[_FakeDbRow]) -> None:
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)

    def commit(self) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, rows: list[_FakeDbRow]) -> None:
        self._rows = rows

    def __enter__(self):
        return _FakeSession(self._rows)

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSessionManager:
    def __init__(self, rows: list[_FakeDbRow]) -> None:
        self._rows = rows

    def session(self):
        return _FakeSessionContext(self._rows)


class _FakeDbRuntime:
    def __init__(self, rows: list[_FakeDbRow]) -> None:
        self.session_manager = _FakeSessionManager(rows)


class _FakeBindResult:
    def __init__(self) -> None:
        self.profile = "default"
        self.folder_name = "test"
        self.folder_id = "folder123"
        self.config_path = "/tmp/config.yaml"
        self.folder_url = "https://drive.google.com/drive/folders/folder123"


class _StubA2AVerifier:
    def __init__(self, valid_token: str = "12345678") -> None:
        self.valid_token = valid_token
        self.verify_calls: list[tuple[str, str]] = []

    def resolve_profile(self, conn) -> str:
        return "default"

    def header_for_profile(self, profile_name: str) -> tuple[str, str | None]:
        assert profile_name == "default"
        return "Authorization", "Bearer"

    async def verify_token_for_profile(self, token: str, profile_name: str):
        self.verify_calls.append((token, profile_name))
        if token == self.valid_token and profile_name == "default":
            return object()
        return None


class _StubJobsRuntime:
    def __init__(self) -> None:
        self.server_id = "ut-jobs-server"
        self.backend_name = "memory"
        self._jobs = {
            "job-1": {
                "job_id": "job-1",
                "status": "succeeded",
                "job_type": "file.convert",
            }
        }

    def list_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        session_id: str | None = None,
        job_type: str | None = None,
    ) -> list[dict]:
        del session_id
        jobs = list(self._jobs.values())
        if status:
            jobs = [job for job in jobs if job.get("status") == status]
        if job_type:
            jobs = [job for job in jobs if job.get("job_type") == job_type]
        return jobs[:limit]

    def queue_status(self) -> dict[str, int]:
        return {"succeeded": 1}

    def get_job(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)


def _profile(tmp_path):
    defaults_yaml = """
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY_PRIMARY}"
        - "${FILE_MCP_API_KEY_SECONDARY}"
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
    limits:
      search_max_results: 5
      search_max_file_mb: 1
      conversion_timeout_s: 10
""".lstrip()
    env_values = {
        "FILE_MCP_API_KEY_PRIMARY": "secret",
        "FILE_MCP_API_KEY_SECONDARY": "",
        "FILE_MCP_ROOT": str(tmp_path),
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=defaults_yaml,
    )


def _run_middleware_request(middleware, *, path: str, method: str = "GET", headers=None):
    sent: list[dict] = []

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers or [],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    return sent


def test_resolve_http_settings_with_base_path() -> None:
    config = HttpServerConfig(
        transport="streamable-http",
        host="0.0.0.0",
        port="8123",
        base_path="/app/v1",
        mcp_path="/mcp",
        health_path="/healthz",
        events_path="/events",
        stateless_http="true",
    )
    settings = resolve_http_settings(config)
    assert settings.host == "0.0.0.0"
    assert settings.port == 8123
    assert settings.mcp_path == "/mcp"
    assert settings.health_path == "/app/v1/healthz"
    assert settings.events_path == "/app/v1/events"
    assert settings.stateless_http is True


def test_deleted_profile_name_preserves_uniqueness_budget() -> None:
    tombstone = _deleted_profile_name("profile-name")

    assert tombstone.startswith("profile-name__deleted_")
    assert len(tombstone) <= 128


def test_merge_active_db_profiles_into_config_overrides_file_seed() -> None:
    config = ServerConfig(
        profiles={
            "default": ProfileConfig.model_validate(
                {
                    "auth": {
                        "api_keys": ["seed-secret"],
                        "header_name": "Authorization",
                        "header_scheme": "Bearer",
                    },
                    "storage": {"backend": "local"},
                    "scope": {"roots": ["/seed/default"]},
                }
            ),
            "db-profile": ProfileConfig.model_validate(
                {
                    "auth": {
                        "api_keys": ["existing-secret"],
                        "header_name": "Authorization",
                        "header_scheme": "Bearer",
                    },
                    "storage": {"backend": "local"},
                    "scope": {"roots": ["/seed/original"]},
                }
            ),
        }
    )
    db_runtime = _FakeDbRuntime(
        [
            _FakeDbRow(
                name="db-profile",
                config_json=json.dumps(
                    {
                        "storage": {"backend": "ftp"},
                        "scope": {"roots": ["/db/override"]},
                    }
                ),
                is_active=True,
            ),
            _FakeDbRow(
                name="inactive-profile",
                config_json=json.dumps(
                    {
                        "storage": {"backend": "s3"},
                        "scope": {"roots": ["/db/inactive"]},
                    }
                ),
                is_active=False,
            ),
        ]
    )

    merged = _merge_active_db_profiles_into_config(config, db_runtime=db_runtime)

    assert merged.profiles["db-profile"].storage.backend == "ftp"
    assert merged.profiles["db-profile"].scope.roots == ["/db/override"]
    assert merged.profiles["db-profile"].auth.api_keys == ["existing-secret"]
    assert "inactive-profile" not in merged.profiles


def test_normalise_profile_mapping_inherits_default_auth_when_missing() -> None:
    normalized = _normalise_profile_mapping(
        {
            "storage": {"backend": "local"},
            "scope": {"roots": ["/db/override"]},
        },
        default_profile={
            "auth": {
                "api_keys": ["default-secret"],
                "header_name": "Authorization",
                "header_scheme": "Bearer",
            }
        },
    )

    assert normalized["auth"]["api_keys"] == ["default-secret"]
    assert normalized["auth"]["header_name"] == "Authorization"
    assert normalized["auth"]["header_scheme"] == "Bearer"


def test_health_middleware_supports_legacy_api_alias_path() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/app/v1/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/api/v1/health"}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200


def test_health_middleware_supports_legacy_root_alias_path() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/app/v1/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/health"}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200


def test_build_tool_registry_wires_real_handlers(tmp_path) -> None:
    profile = _profile(tmp_path)
    registry = build_tool_registry(profile)
    write_handler = registry.get("write_file").handler
    read_handler = registry.get("read_file").handler

    target = tmp_path / "sample.txt"
    write_result = write_handler(str(target), "hello")
    assert write_result["ok"] is True
    assert read_handler(str(target)) == "hello"


def test_build_tool_registry_includes_backend_status(tmp_path) -> None:
    profile = _profile(tmp_path)
    registry = build_tool_registry(profile)
    status = registry.get("backend_status").handler()
    assert status["profile"] == "default"
    assert status["active_backend"] == "local"
    assert isinstance(status["states"], dict)


def test_build_tool_registry_passes_max_results_to_local_search(tmp_path, monkeypatch) -> None:
    import file_mcp_server.server_runtime as server_runtime_module

    profile = _profile(tmp_path)
    registry = build_tool_registry(profile)
    captured: dict[str, int | None] = {}

    def _fake_search_paths(query: str, **kwargs):
        del query
        captured["paths_max_results"] = kwargs.get("max_results")
        return []

    def _fake_search_content(query: str, **kwargs):
        del query
        captured["content_max_results"] = kwargs.get("max_results")
        return []

    monkeypatch.setattr(server_runtime_module, "search_paths", _fake_search_paths)
    monkeypatch.setattr(server_runtime_module, "search_content", _fake_search_content)

    registry.get("search_paths").handler("alpha")
    registry.get("search_content").handler("alpha")

    assert captured["paths_max_results"] == profile.limits.search_max_results
    assert captured["content_max_results"] == profile.limits.search_max_results


def test_health_middleware_returns_ok() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/health"}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    status = sent[0]["status"]
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert status == 200
    assert body["status"] == "ok"


def test_health_middleware_returns_status_metrics() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/status"}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert set(body.keys()) >= {
        "uptime_seconds",
        "uptime",
        "memory_mb",
        "memory_percent",
        "cpu_percent",
        "disk_percent",
        "active_connections",
        "service_metrics",
    }
    assert set(body["service_metrics"].keys()) >= {
        "file_count",
        "profile_count",
        "storage_used_mb",
    }


def test_a2a_health_is_public_without_auth() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = _StubA2AVerifier()
    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        a2a_auth_verifier=verifier,
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "GET", "path": "/a2a/health", "headers": []}

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert body["status"] == "ok"
    assert verifier.verify_calls == []


def test_a2a_health_ignores_auth_header_verifier_contract() -> None:
    sent = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = _StubA2AVerifier(valid_token="12345678")
    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        a2a_auth_verifier=verifier,
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/a2a/health",
            "headers": [(b"authorization", b"Bearer 12345678")],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert body["status"] == "ok"
    assert body["a2a"]["base_path"] == "/a2a"
    assert verifier.verify_calls == []


def test_admin_profiles_api_route_supports_api_prefix_alias() -> None:
    sent = []

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = _StubA2AVerifier(valid_token="12345678")
    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        a2a_auth_verifier=verifier,
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/admin/profiles",
            "headers": [(b"authorization", b"Bearer 12345678")],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert body["ok"] is True
    assert "profiles" in body
    assert verifier.verify_calls == [("12345678", "default")]


def test_health_middleware_jobs_route_lists_jobs() -> None:
    sent = []

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = _StubA2AVerifier(valid_token="12345678")
    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        a2a_auth_verifier=verifier,
        jobs_runtime_provider=lambda _profile_name: _StubJobsRuntime(),
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/jobs",
            "headers": [(b"authorization", b"Bearer 12345678")],
            "query_string": b"limit=5&status=succeeded",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    payload = json.loads(sent[1]["body"].decode("utf-8"))
    assert payload["ok"] is True
    assert payload["queue_backend"] == "memory"
    assert payload["jobs"][0]["job_id"] == "job-1"


def test_health_middleware_jobs_route_reads_single_job() -> None:
    sent = []

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = _StubA2AVerifier(valid_token="12345678")
    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        a2a_auth_verifier=verifier,
        jobs_runtime_provider=lambda _profile_name: _StubJobsRuntime(),
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/jobs/job-1",
            "headers": [(b"authorization", b"Bearer 12345678")],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 200
    payload = json.loads(sent[1]["body"].decode("utf-8"))
    assert payload["ok"] is True
    assert payload["job"]["job_id"] == "job-1"


def test_build_tool_registry_convert_file_reports_job_id(tmp_path) -> None:
    profile = _profile(tmp_path)
    jobs_runtime = FileMcpJobsRuntime.from_profile(
        profile,
        profile_name="default",
        fallback_sql_url="sqlite:///",
    )
    assert jobs_runtime is not None
    registry = build_tool_registry(profile, jobs_runtime=jobs_runtime)

    src = tmp_path / "doc.txt"
    out = tmp_path / "doc.md"
    src.write_text("hello", encoding="utf-8")
    result = registry.get("convert_file").handler(
        str(src),
        "md",
        str(out),
        backend="builtin-text-copy",
    )

    assert result["ok"] is True
    assert "job_id" in result
    job = jobs_runtime.get_job(str(result["job_id"]))
    assert job is not None
    assert job["status"] == "succeeded"


def test_streamable_http_accept_compatibility_middleware_patches_json_only_accept() -> (
    None
):
    captured = {}

    async def fake_app(scope, receive, send) -> None:
        captured["scope"] = scope
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = StreamableHttpAcceptCompatibilityMiddleware(fake_app, mcp_path="/mcp")
    sent = []

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [(b"accept", b"application/json")],
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    asyncio.run(_run())
    assert sent[0]["status"] == 204
    headers = {
        (k.decode("latin-1") if isinstance(k, bytes) else str(k)).lower(): (
            v.decode("latin-1") if isinstance(v, bytes) else str(v)
        )
        for k, v in captured["scope"]["headers"]
    }
    accept = headers["accept"].lower()
    assert "application/json" in accept
    assert "text/event-stream" in accept


def test_resolve_auth_api_key_value_unwraps_nested_env_placeholders() -> None:
    previous_outer = runtime_env.get("W28A355_OUTER_KEY")
    previous_inner = runtime_env.get("W28A355_INNER_KEY")
    runtime_env["W28A355_OUTER_KEY"] = "${W28A355_INNER_KEY}"
    runtime_env["W28A355_INNER_KEY"] = "resolved-secret-key"
    try:
        assert (
            _resolve_auth_api_key_value(
                "${W28A355_OUTER_KEY}",
                vault_client=None,
            )
            == "resolved-secret-key"
        )
    finally:
        if previous_outer is None:
            runtime_env.pop("W28A355_OUTER_KEY", None)
        else:
            runtime_env["W28A355_OUTER_KEY"] = previous_outer
        if previous_inner is None:
            runtime_env.pop("W28A355_INNER_KEY", None)
        else:
            runtime_env["W28A355_INNER_KEY"] = previous_inner


def test_resolve_auth_api_key_value_returns_empty_for_unresolved_placeholder() -> None:
    previous = runtime_env.get("W28A355_MISSING_KEY")
    runtime_env.pop("W28A355_MISSING_KEY", None)
    try:
        assert (
            _resolve_auth_api_key_value(
                "${W28A355_MISSING_KEY}",
                vault_client=None,
            )
            == ""
        )
    finally:
        if previous is not None:
            runtime_env["W28A355_MISSING_KEY"] = previous


def test_root_route_serves_spa_index_from_configured_dist(tmp_path) -> None:
    prev_ui_dist = runtime_env.get("FILE_MCP_UI_DIST_PATH")
    dist = tmp_path / "ui-dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body>file-mcp-ui-shell</body></html>",
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_UI_DIST_PATH"] = str(dist)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="local",
        transport="streamable-http",
    )

    try:
        sent = _run_middleware_request(
            middleware, path="/", headers=[(b"accept", b"text/html")]
        )
        assert sent[0]["status"] == 200
        assert b"file-mcp-ui-shell" in sent[1]["body"]
    finally:
        if prev_ui_dist is None:
            runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
        else:
            runtime_env["FILE_MCP_UI_DIST_PATH"] = prev_ui_dist


def test_root_route_with_api_accept_serves_spa_index(tmp_path) -> None:
    prev_ui_dist = runtime_env.get("FILE_MCP_UI_DIST_PATH")
    dist = tmp_path / "ui-dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body>file-mcp-ui-shell</body></html>",
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_UI_DIST_PATH"] = str(dist)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    try:
        sent = _run_middleware_request(
            middleware, path="/", headers=[(b"accept", b"application/json")]
        )
        assert sent[0]["status"] == 200
        assert b"file-mcp-ui-shell" in sent[1]["body"]
    finally:
        if prev_ui_dist is None:
            runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
        else:
            runtime_env["FILE_MCP_UI_DIST_PATH"] = prev_ui_dist


def test_health_middleware_google_drive_page_locks_profile_from_query() -> None:
    sent = []
    previous = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    previous_profiles = runtime_env.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    previous_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,s3,webdav,ftp,google_drive"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/google-drive",
            "query_string": b"profile=google_drive",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "scheme": "http",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        assert "Profile is fixed for this authorisation flow." in body
        assert "value='google_drive'" in body
    finally:
        if previous is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = previous
        if previous_profiles is None:
            runtime_env.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = previous_profiles
        if previous_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = previous_token


def test_runtime_config_endpoint_returns_dynamic_script() -> None:
    previous = {
        key: runtime_env.get(key)
        for key in (
            "FILE_MCP_UI_ENV",
            "FILE_MCP_UI_API_BASE_URL",
            "FILE_MCP_UI_AUTH_MODE",
            "FILE_MCP_UI_AUDIT_LOG_PATH",
            "FILE_MCP_UI_DEFAULT_BROWSE_PATH",
            "FILE_MCP_UI_PROFILE_STORE_PATH",
        )
    }
    runtime_env["FILE_MCP_UI_ENV"] = "preprod"
    runtime_env["FILE_MCP_UI_API_BASE_URL"] = "https://api.filemcp.example"
    runtime_env["FILE_MCP_UI_AUTH_MODE"] = "api_key"
    runtime_env["FILE_MCP_UI_AUDIT_LOG_PATH"] = "working/preprod/audit.jsonl"
    runtime_env["FILE_MCP_UI_DEFAULT_BROWSE_PATH"] = "storage"
    runtime_env["FILE_MCP_UI_PROFILE_STORE_PATH"] = "working/preprod/profiles.json"

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    try:
        sent = _run_middleware_request(middleware, path="/runtime-config.js")
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        assert "window.__RUNTIME_CONFIG__ = Object.assign(" in body
        match = re.search(r"Object\.assign\(\s*(\{.*\})\s*,", body, re.DOTALL)
        assert match is not None
        payload = json.loads(match.group(1))
        assert payload["ENV"] == "preprod"
        assert payload["API_BASE_URL"] == "https://api.filemcp.example"
        assert payload["AUTH_MODE"] == "api_key"
        assert payload["AUDIT_LOG_PATH"] == "working/preprod/audit.jsonl"
        assert payload["DEFAULT_BROWSE_PATH"] == "storage"
        assert payload["PROFILE_STORE_PATH"] == "working/preprod/profiles.json"
    finally:
        for key, value in previous.items():
            if value is None:
                runtime_env.pop(key, None)
            else:
                runtime_env[key] = value


def test_runtime_config_endpoint_scopes_audit_log_path_to_selected_profile_root() -> None:
    previous = {
        key: runtime_env.get(key)
        for key in (
            "FILE_MCP_UI_AUDIT_LOG_PATH",
            "FILE_MCP_UI_DEFAULT_BROWSE_PATH",
        )
    }
    runtime_env.pop("FILE_MCP_UI_AUDIT_LOG_PATH", None)
    runtime_env.pop("FILE_MCP_UI_DEFAULT_BROWSE_PATH", None)

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )
    middleware._list_profile_payloads = lambda: [  # type: ignore[method-assign]
        {
            "name": "default",
            "profile": {
                "scope": {"roots": ["./working"]},
                "audit": {"log_path": "./working/test-env-st-local-docker/audit.log.jsonl"},
            },
        }
    ]

    try:
        sent = _run_middleware_request(middleware, path="/runtime-config.js")
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        match = re.search(r"Object\.assign\(\s*(\{.*\})\s*,", body, re.DOTALL)
        assert match is not None
        payload_json = match.group(1).replace("__origin", '"http://127.0.0.1:38190"')
        payload = json.loads(payload_json)
        assert payload["DEFAULT_BROWSE_PATH"] == "."
        assert payload["AUDIT_LOG_PATH"] == "./test-env-st-local-docker/audit.log.jsonl"
    finally:
        for key, value in previous.items():
            if value is None:
                runtime_env.pop(key, None)
            else:
                runtime_env[key] = value


def test_ui_routes_serve_spa_index_from_configured_dist(tmp_path) -> None:
    prev_ui_dist = runtime_env.get("FILE_MCP_UI_DIST_PATH")
    dist = tmp_path / "ui-dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body>file-mcp-ui-shell</body></html>",
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_UI_DIST_PATH"] = str(dist)

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    try:
        for route in (
            "/ui",
            "/ui/dashboard",
            "/dashboard",
            "/unknown-route-that-does-not-exist",
            "/jobs",
            "/api-docs",
            "/admin/users",
            "/admin/groups",
            "/admin/api-keys",
            "/mcp-console",
            "/a2a-console",
        ):
            sent = _run_middleware_request(
                middleware, path=route, headers=[(b"accept", b"text/html")]
            )
            assert sent[0]["status"] == 200
            assert b"file-mcp-ui-shell" in sent[1]["body"]
    finally:
        if prev_ui_dist is None:
            runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
        else:
            runtime_env["FILE_MCP_UI_DIST_PATH"] = prev_ui_dist


def test_non_ui_api_paths_do_not_fallback_to_spa(tmp_path) -> None:
    prev_ui_dist = runtime_env.get("FILE_MCP_UI_DIST_PATH")
    dist = tmp_path / "ui-dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body>file-mcp-ui-shell</body></html>",
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_UI_DIST_PATH"] = str(dist)

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"not-found"})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    try:
        sent = _run_middleware_request(middleware, path="/api/unknown")
        assert sent[0]["status"] == 404
        assert sent[1]["body"] == b"not-found"
    finally:
        if prev_ui_dist is None:
            runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
        else:
            runtime_env["FILE_MCP_UI_DIST_PATH"] = prev_ui_dist


def test_ui_assets_are_served_from_dist(tmp_path) -> None:
    prev_ui_dist = runtime_env.get("FILE_MCP_UI_DIST_PATH")
    dist = tmp_path / "ui-dist"
    assets = dist / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    asset_file = assets / "app.js"
    asset_file.write_text("console.log('asset-ok');", encoding="utf-8")
    runtime_env["FILE_MCP_UI_DIST_PATH"] = str(dist)

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    try:
        for route in ("/assets/app.js", "/ui/assets/app.js"):
            sent = _run_middleware_request(middleware, path=route)
            assert sent[0]["status"] == 200
            assert sent[1]["body"] == b"console.log('asset-ok');"
    finally:
        if prev_ui_dist is None:
            runtime_env.pop("FILE_MCP_UI_DIST_PATH", None)
        else:
            runtime_env["FILE_MCP_UI_DIST_PATH"] = prev_ui_dist


def test_health_middleware_serves_google_drive_admin_page() -> None:
    sent = []
    previous = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    previous_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/google-drive",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "scheme": "http",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        assert b"Google Drive Profile Setup" in sent[1]["body"]
    finally:
        if previous is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = previous
        if previous_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = previous_token


def test_health_middleware_google_drive_page_uses_forwarded_proto() -> None:
    sent = []
    previous = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    previous_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/google-drive",
            "headers": [
                (b"host", b"filemcpserver0.cloud-dog.net"),
                (b"x-forwarded-proto", b"https"),
            ],
            "scheme": "http",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        assert (
            "https://filemcpserver0.cloud-dog.net/admin/google-drive/callback" in body
        )
    finally:
        if previous is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = previous
        if previous_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = previous_token


def test_health_middleware_google_drive_page_prefills_config_and_masks_secret(
    tmp_path,
) -> None:
    sent = []
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_profiles = runtime_env.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    prev_config = runtime_env.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    prev_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,google_drive"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "profiles:\n"
            "  google_drive:\n"
            "    storage:\n"
            "      backend: google_drive\n"
            "      google_drive:\n"
            "        user_email: gary@example.com\n"
            "        folder_id: folder123\n"
            "        client_id: client-abc\n"
            "        client_secret: secret-xyz\n"
            "        redirect_uri: urn:ietf:wg:oauth:2.0:oob\n"
            "        token_uri: https://oauth2.googleapis.com/token\n"
        ),
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/google-drive",
            "query_string": b"profile=google_drive",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "scheme": "http",
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        assert 'value="gary@example.com"' in body
        assert 'value="client-abc"' in body
        assert "folder123" in body
        assert 'value="********"' in body
        assert "secret-xyz" not in body
        assert (
            'name="redirect_uri" value="http://127.0.0.1:8000/admin/google-drive/callback"'
            in body
        )
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_profiles is None:
            runtime_env.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = prev_profiles
        if prev_config is None:
            runtime_env.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config
        if prev_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token


def test_health_middleware_google_drive_start_reuses_masked_secret(
    tmp_path, monkeypatch
) -> None:
    sent = []
    captured: dict[str, str] = {}
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_profiles = runtime_env.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    prev_config = runtime_env.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    prev_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,google_drive"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "profiles:\n"
            "  google_drive:\n"
            "    storage:\n"
            "      backend: google_drive\n"
            "      google_drive:\n"
            "        folder_url: https://drive.google.com/drive/folders/folder123\n"
            "        client_id: client-abc\n"
            "        client_secret: secret-xyz\n"
            "        redirect_uri: urn:ietf:wg:oauth:2.0:oob\n"
            "        token_uri: https://oauth2.googleapis.com/token\n"
        ),
        encoding="utf-8",
    )
    runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

    def _fake_begin_oauth(data: dict[str, str]) -> str:
        captured.update(data)
        return "https://accounts.google.com/o/oauth2/v2/auth?state=test"

    monkeypatch.setattr("file_mcp_server.server_runtime.begin_oauth", _fake_begin_oauth)

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/admin/google-drive/start",
            "headers": [
                (b"host", b"127.0.0.1:8000"),
                (b"content-type", b"application/x-www-form-urlencoded"),
            ],
            "scheme": "http",
        }

        async def receive():
            return {
                "type": "http.request",
                "body": b"profile=google_drive&client_secret=%2A%2A%2A%2A%2A%2A%2A%2A",
                "more_body": False,
            }

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 302
        assert captured["profile"] == "google_drive"
        assert captured["client_id"] == "client-abc"
        assert captured["client_secret"] == "secret-xyz"
        assert captured["folder_input"].endswith("/folder123")
        assert captured["redirect_uri"].endswith("/admin/google-drive/callback")
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_profiles is None:
            runtime_env.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = prev_profiles
        if prev_config is None:
            runtime_env.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config
        if prev_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token


def test_health_middleware_reload_requires_admin_gate() -> None:
    sent = []
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "false"

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        reload_callback=lambda: {"profile": "default", "reloaded": True},
    )

    async def _run() -> None:
        scope = {"type": "http", "method": "POST", "path": "/admin/reload"}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled


def test_health_middleware_reload_enforces_token_and_returns_json() -> None:
    sent_unauthorized = []
    sent_authorized = []
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = "secret-token"

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        reload_callback=lambda: {"profile": "default", "reloaded": True},
    )

    async def _run(scope, sent) -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(
            _run(
                {"type": "http", "method": "POST", "path": "/admin/reload"},
                sent_unauthorized,
            )
        )
        assert sent_unauthorized[0]["status"] == 401

        asyncio.run(
            _run(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/admin/reload",
                    "headers": [(b"x-admin-token", b"secret-token")],
                },
                sent_authorized,
            )
        )
        assert sent_authorized[0]["status"] == 200
        payload = json.loads(sent_authorized[1]["body"].decode("utf-8"))
        assert payload["ok"] is True
        assert payload["result"]["reloaded"] is True
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token


def test_google_drive_callback_applies_reload_when_enabled(monkeypatch) -> None:
    sent = []
    prev_enabled = runtime_env.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_token = runtime_env.get("FILE_MCP_ADMIN_UI_TOKEN")
    runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
    monkeypatch.setattr(
        "file_mcp_server.server.complete_oauth_callback",
        lambda **kwargs: _FakeBindResult(),
    )
    reload_calls: list[bool] = []

    async def fake_app(
        scope, receive, send
    ) -> None:  # pragma: no cover - fallback path
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    def _reload():
        reload_calls.append(True)
        return {"profile": "default", "reloaded": True}

    middleware = HealthCheckMiddleware(
        fake_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        reload_callback=_reload,
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/google-drive/callback",
            "query_string": b"state=s123&code=c123",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        body = sent[1]["body"].decode("utf-8")
        assert "Google Drive linked successfully" in body
        assert "hot-reloaded" in body
        assert len(reload_calls) == 1
    finally:
        if prev_enabled is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_token is None:
            runtime_env.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            runtime_env["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token
