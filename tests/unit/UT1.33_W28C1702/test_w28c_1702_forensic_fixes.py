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

"""file-mcp-server — UT for W28C-1702 forensic fixes.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Unit tests for FM5 (profile_names collapse), FM3 (per-request
profile dispatch + schema), FM7 (search_paths/search_path_names), FM8 (GDrive
OAuth callback DB persistence + container-recreate survival), FM1 (server-side
profile status), FM9 (admin-form banner + narrowed localStorage).
Tests: UT1.33
"""

from __future__ import annotations

from tests.env_runtime import runtime_env  # noqa: F401  (autouse env loader)

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

from tests.config_helpers import build_profile

from file_mcp_server import google_drive_admin as admin
from file_mcp_server.db.models import FileStorageProfile
from file_mcp_server.db.runtime import initialise_database, shutdown_database
from file_mcp_server.mcp_api_kit_layer import build_tool_contracts
from file_mcp_server.server import HealthCheckMiddleware, build_tool_registry
from file_mcp_server.server_runtime import create_profile_tool_handler
from file_tools.config.models import ProfileConfig, ServerConfig
from file_tools.tools import ToolDefinition, ToolMeta, ToolRegistry
from file_tools.tools.schemas import SearchPathsInput


async def _noop_app(scope, receive, send) -> None:  # pragma: no cover - fallback
    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _two_profile_config() -> ServerConfig:
    mk = lambda backend, roots: ProfileConfig.model_validate(
        {
            "auth": {
                "api_keys": ["secret"],
                "header_name": "Authorization",
                "header_scheme": "Bearer",
            },
            "storage": {"backend": backend},
            "scope": {"roots": roots},
        }
    )
    return ServerConfig(
        profiles={
            "default": mk("local", ["/workspace"]),
            "google_drive": mk("local", ["/workspace/gd"]),
        }
    )


def _local_profile(tmp_path: Path) -> ProfileConfig:
    yaml = """
profiles:
  default:
    storage:
      backend: local
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
    limits:
      search_max_results: 5
      search_max_file_mb: 1
      conversion_timeout_s: 10
""".lstrip()
    return build_profile(
        tmp_path,
        env_values={"FILE_MCP_API_KEY_PRIMARY": "secret", "FILE_MCP_ROOT": str(tmp_path)},
        defaults_yaml=yaml,
        config_yaml=yaml,
    )


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    monkeypatch.delenv("CLOUD_DOG__DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__URL", raising=False)


# ───────────────────────────── FM5 ─────────────────────────────

def test_fm5_profile_names_reflect_db_merged_config_not_collapsed_env(monkeypatch) -> None:
    # Simulate main.py's startup collapse: env says a single profile.
    monkeypatch.setenv("FILE_MCP_ACTIVE_PROFILE_NAMES", "default")
    mw = HealthCheckMiddleware(
        _noop_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        config=_two_profile_config(),
    )
    # FM5: the DB-merged config (2 profiles) wins over the collapsed env (1).
    assert len(mw.profile_names) >= 2
    assert set(mw.profile_names) == {"default", "google_drive"}


def test_fm5_status_profile_count_matches_active_profiles(monkeypatch) -> None:
    monkeypatch.setenv("FILE_MCP_ACTIVE_PROFILE_NAMES", "default")
    mw = HealthCheckMiddleware(
        _noop_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
        config=_two_profile_config(),
    )
    sent: list[dict] = []

    async def _run() -> None:
        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent.append(message)

        await mw({"type": "http", "method": "GET", "path": "/status"}, receive, send)

    asyncio.run(_run())
    body = json.loads(sent[1]["body"].decode("utf-8"))
    assert body["service_metrics"]["profile_count"] == 2


# ───────────────────────────── FM3 ─────────────────────────────

def test_fm3_explicit_profile_arg_routes_to_named_registry() -> None:
    calls: dict[str, object] = {}

    def raw_handler(path: str = "."):
        calls["raw_kwargs"] = {"path": path}
        return {"ok": True, "path": path}

    fake_registry = SimpleNamespace(
        audit_writer=None,
        endpoint_health_manager=None,
        storage_backend_name=None,
        profile_config=None,
        get=lambda name: SimpleNamespace(handler=raw_handler),
    )

    def provider(profile_name=None):
        calls["selected_profile"] = profile_name
        return fake_registry

    handler = create_profile_tool_handler(
        provider, "backend_status", default_profile_name="default"
    )
    result = handler(path="/", profile="google_drive")

    # FM3: the explicit `profile` arg selected the registry...
    assert calls["selected_profile"] == "google_drive"
    # ...was NOT forwarded to the raw tool handler (which can't accept it)...
    assert "profile" not in calls["raw_kwargs"]
    assert result["ok"] is True
    # ...and is advertised on the wrapper signature so it is not stripped.
    assert "profile" in inspect.signature(handler).parameters


def test_fm3_build_tool_contracts_advertise_profile() -> None:
    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            meta=ToolMeta(name="ping", description="x"),
            handler=lambda: {"ok": True},
        )
    )
    contracts = build_tool_contracts(
        lambda *a, **k: reg,
        object(),
        seed_registry=reg,
        profile_tool_factory=lambda name: (lambda **k: {"ok": True}),
    )
    props = contracts["ping"].input_schema.get("properties", {})
    assert "profile" in props
    assert props["profile"]["type"] == "string"


# ───────────────────────────── FM7 ─────────────────────────────

def test_fm7_search_paths_input_advertises_query() -> None:
    schema = SearchPathsInput.model_json_schema()
    assert "query" in schema["properties"]
    assert "query" in schema.get("required", [])


def test_fm7_search_paths_and_alias_registered_with_schema(tmp_path) -> None:
    registry = build_tool_registry(_local_profile(tmp_path))
    names = [d.meta.name for d in registry.list_tools()]
    assert "search_paths" in names
    assert "search_path_names" in names  # was Unknown tool
    for tool in ("search_paths", "search_path_names"):
        model = registry.get(tool).schema_def.input_model
        assert model is SearchPathsInput
    # The advertised field matches the handler's `query` parameter (no TypeError).
    assert registry.get("search_paths").handler("nonexistent-xyz") == {"matches": []}


# ───────────────────────────── FM8 ─────────────────────────────

def test_fm8_gdrive_tokens_persist_across_new_session_manager(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "fm8.db"
    _configure_sqlite_env(monkeypatch, db_path)
    runtime1 = initialise_database(force_reinit=True)
    try:
        row_id = admin._persist_profile_google_drive_to_db(
            db_session_manager=runtime1.session_manager,
            file_storage_profile_model=FileStorageProfile,
            profile="google_drive",
            user_email="ops@example.test",
            folder_id="FID123",
            folder_url="https://drive.example/FID123",
            client_id="cid",
            client_secret="csec",
            refresh_token="rtok",
            access_token="atok",
            redirect_uri="https://x/callback",
            token_uri="https://oauth/token",
        )
        assert row_id
    finally:
        shutdown_database()

    # Simulate container recreate: a brand-new session manager over the SAME
    # (bind-mounted, in this test temp) SQLite file.
    runtime2 = initialise_database(force_reinit=True)
    try:
        with runtime2.session_manager.session() as session:
            row = (
                session.query(FileStorageProfile)
                .filter_by(name="google_drive", is_active=True)
                .first()
            )
            assert row is not None
            gd = json.loads(row.config_json)["storage"]["google_drive"]
            assert gd["refresh_token"] == "rtok"
            assert gd["folder_id"] == "FID123"
            assert gd["user_email"] == "ops@example.test"
    finally:
        shutdown_database()


def test_fm8_complete_oauth_callback_accepts_db_injection_kwargs() -> None:
    params = inspect.signature(admin.complete_oauth_callback).parameters
    assert "db_session_manager" in params
    assert "file_storage_profile_model" in params
    assert "reload_callback" in params
    assert "db_row_id" in {f.name for f in admin.GoogleDriveBindResult.__dataclass_fields__.values()}


# ───────────────────────────── FM1 ─────────────────────────────

def test_fm1_compute_profile_status_per_backend() -> None:
    mw = HealthCheckMiddleware(
        _noop_app,
        health_path="/health",
        profile_name="default",
        transport="streamable-http",
    )
    full_gd = {
        "google_drive": {
            "refresh_token": "r",
            "folder_id": "f",
            "user_email": "u@e",
            "client_id": "c",
            "client_secret": "s",
        }
    }
    assert mw._compute_profile_status(backend="google_drive", storage=full_gd, roots=[])["status"] == "configured"
    partial = {"google_drive": {"refresh_token": "r", "folder_id": "f"}}
    assert mw._compute_profile_status(backend="google_drive", storage=partial, roots=[])["status"] == "partially_configured"
    assert mw._compute_profile_status(backend="google_drive", storage={}, roots=[])["status"] == "not_configured"
    assert mw._compute_profile_status(backend="local", storage={}, roots=["/x"])["status"] == "configured"
    assert mw._compute_profile_status(backend="local", storage={}, roots=[])["status"] == "not_configured"
    s3 = {"s3": {"endpoint": "e", "bucket": "b", "access_key": "a", "secret_key": "k"}}
    assert mw._compute_profile_status(backend="s3", storage=s3, roots=[])["status"] == "configured"


# ───────────────────────────── FM9 ─────────────────────────────

def test_fm9_localstorage_narrowed_to_operator_defaults() -> None:
    html = admin.render_setup_page(callback_url="http://x/cb", profiles=["default"])
    fields_block = html.split("var fields =", 1)[1].split("]", 1)[0]
    assert "redirect_uri" in fields_block
    assert "token_uri" in fields_block
    # Credentials / identity are NEVER remembered locally (the FM9 fix).
    for leaked in ("user_email", "folder_input", "client_id"):
        assert leaked not in fields_block


def test_fm9_status_banner_is_rendered() -> None:
    html = admin.render_setup_page(
        callback_url="http://x/cb",
        profiles=["default"],
        status_banner="<div id='gd-banner'>NOT CONFIGURED</div>",
    )
    assert "id='gd-banner'" in html
    assert "NOT CONFIGURED" in html
