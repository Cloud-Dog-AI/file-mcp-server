from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os

from tests.config_helpers import build_profile
from file_tools.config.models import HttpServerConfig
from file_mcp_server.endpoint_health import ENDPOINT_HEALTH_MANAGER, EndpointState
from file_mcp_server.server import (
    HealthCheckMiddleware,
    StreamableHttpAcceptCompatibilityMiddleware,
    build_tool_registry,
    resolve_http_settings,
)


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


def test_health_middleware_supports_legacy_api_alias_path() -> None:
    sent = []

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
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

    async def fake_app(scope, receive, send) -> None:  # pragma: no cover - fallback path
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


def test_a2a_health_requires_auth() -> None:
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
    assert sent[0]["status"] == 401
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert body["ok"] is False
    assert verifier.verify_calls == []


def test_a2a_health_uses_auth_verifier_contract() -> None:
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
    assert verifier.verify_calls == [("12345678", "default")]


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


def test_root_status_page_returns_html_summary(tmp_path) -> None:
    sent = []
    prev_config = os.environ.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "profiles:\n"
            "  local:\n"
            "    storage:\n"
            "      backend: local\n"
            "  s3:\n"
            "    storage:\n"
            "      backend: s3\n"
        ),
        encoding="utf-8",
    )
    os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

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

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"accept", b"text/html")],
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
        assert "file-mcp-server status" in body
        assert "Configured Profiles" in body
        assert "local" in body
        assert "s3" in body
        assert "status-dot" in body
        assert "Signal" in body
        assert "Action" in body
    finally:
        if prev_config is None:
            os.environ.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config


def test_root_status_page_shows_google_drive_authorize_button_when_token_missing(
    tmp_path,
) -> None:
    sent = []
    prev_config = os.environ.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    prev_admin = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "profiles:\n"
            "  gdrive:\n"
            "    storage:\n"
            "      backend: google_drive\n"
            "      google_drive:\n"
            "        folder_id: folder123\n"
            "        client_id: client-abc\n"
            "        client_secret: secret-xyz\n"
            "        refresh_token: ''\n"
            "        access_token: ''\n"
        ),
        encoding="utf-8",
    )
    os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

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
            "path": "/",
            "headers": [(b"accept", b"text/html")],
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
        assert "Authorize Google Drive" in body
        assert "/admin/google-drive?profile=gdrive" in body
    finally:
        if prev_config is None:
            os.environ.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config
        if prev_admin is None:
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_admin


def test_health_middleware_google_drive_page_locks_profile_from_query() -> None:
    sent = []
    previous = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    previous_profiles = os.environ.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,s3,webdav,ftp,google_drive"

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
        assert "Profile is fixed for this authorization flow." in body
        assert "value='google_drive'" in body
    finally:
        if previous is None:
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = previous
        if previous_profiles is None:
            os.environ.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = previous_profiles


def test_root_status_page_returns_json_for_api_accept(tmp_path) -> None:
    sent = []
    prev_config = os.environ.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "profiles:\n  ftp:\n    storage:\n      backend: ftp\n",
        encoding="utf-8",
    )
    os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

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
    ENDPOINT_HEALTH_MANAGER._states.clear()
    ENDPOINT_HEALTH_MANAGER._set_state(
        "ftp",
        EndpointState(
            backend="ftp",
            status="healthy",
            reason="startup_probe_ok",
            last_error="",
            updated_at=datetime.now(timezone.utc).isoformat(),
            failures_in_window=0,
            consecutive_failures=0,
            retries_used=0,
            requires_restart=False,
        ),
    )

    async def _run() -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"accept", b"application/json")],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)

    try:
        asyncio.run(_run())
        assert sent[0]["status"] == 200
        payload = json.loads(sent[1]["body"].decode("utf-8"))
        assert payload["status"] == "ok"
        assert payload["profiles"]["ftp"] == "ftp"
        assert payload["profile_health"]["ftp"]["status"] == "healthy"
        assert payload["profile_health"]["ftp"]["signal"] == "green"
    finally:
        ENDPOINT_HEALTH_MANAGER._states.clear()
        if prev_config is None:
            os.environ.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config


def test_health_middleware_serves_google_drive_admin_page() -> None:
    sent = []
    previous = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"

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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = previous


def test_health_middleware_google_drive_page_uses_forwarded_proto() -> None:
    sent = []
    previous = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"

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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = previous


def test_health_middleware_google_drive_page_prefills_config_and_masks_secret(
    tmp_path,
) -> None:
    sent = []
    prev_enabled = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_profiles = os.environ.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    prev_config = os.environ.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,google_drive"
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
    os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_profiles is None:
            os.environ.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = prev_profiles
        if prev_config is None:
            os.environ.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config


def test_health_middleware_google_drive_start_reuses_masked_secret(
    tmp_path, monkeypatch
) -> None:
    sent = []
    captured: dict[str, str] = {}
    prev_enabled = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_profiles = os.environ.get("FILE_MCP_ACTIVE_PROFILE_NAMES")
    prev_config = os.environ.get("FILE_MCP_ACTIVE_CONFIG_PATH")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = "default,google_drive"
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
    os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(config_path)

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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_profiles is None:
            os.environ.pop("FILE_MCP_ACTIVE_PROFILE_NAMES", None)
        else:
            os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = prev_profiles
        if prev_config is None:
            os.environ.pop("FILE_MCP_ACTIVE_CONFIG_PATH", None)
        else:
            os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = prev_config


def test_health_middleware_reload_requires_admin_gate() -> None:
    sent = []
    prev_enabled = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "false"

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
        assert sent[0]["status"] == 404
    finally:
        if prev_enabled is None:
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled


def test_health_middleware_reload_enforces_token_and_returns_json() -> None:
    sent_unauthorized = []
    sent_authorized = []
    prev_enabled = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    prev_token = os.environ.get("FILE_MCP_ADMIN_UI_TOKEN")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
    os.environ["FILE_MCP_ADMIN_UI_TOKEN"] = "secret-token"

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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
        if prev_token is None:
            os.environ.pop("FILE_MCP_ADMIN_UI_TOKEN", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_TOKEN"] = prev_token


def test_google_drive_callback_applies_reload_when_enabled(monkeypatch) -> None:
    sent = []
    prev_enabled = os.environ.get("FILE_MCP_ADMIN_UI_ENABLED")
    os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = "true"
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
            os.environ.pop("FILE_MCP_ADMIN_UI_ENABLED", None)
        else:
            os.environ["FILE_MCP_ADMIN_UI_ENABLED"] = prev_enabled
