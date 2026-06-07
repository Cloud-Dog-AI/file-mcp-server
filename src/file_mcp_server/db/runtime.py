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

"""
file-mcp-server — file_mcp_server/db/runtime.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Database runtime module for runtime.py.
"""

from __future__ import annotations

from os import getenv as read_env_var
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from cloud_dog_storage import path_utils

from cloud_dog_db import (
    DatabaseSettings,
    MigrationRunner,
    SyncSessionManager,
    build_sync_engine,
    probe_database,
)
from cloud_dog_db.migrations.runner import MigrationConfig


@dataclass(slots=True)
class PlatformDatabaseRuntime:
    settings: DatabaseSettings
    engine: Engine
    session_manager: SyncSessionManager
    migration_runner: MigrationRunner


_RUNTIME_LOCK = Lock()
_RUNTIME: PlatformDatabaseRuntime | None = None


def _project_root() -> Path:
    """Handle project root."""
    current = path_utils.as_path(path_utils.resolve_path(__file__))
    for candidate in current.parents:
        if path_utils.exists(str(candidate / "pyproject.toml")):
            return candidate
    return current.parents[4]


def _default_sqlite_path() -> str:
    """Handle default sqlite path."""
    return "./database/file_mcp.db"


def _env_value(*names: str) -> str | None:
    """Handle env value."""
    for name in names:
        value = read_env_var(name, "").strip()
        if value:
            return value
    return None


def _settings_from_env() -> DatabaseSettings:
    """Handle settings from env."""
    explicit_url = _env_value(
        "CLOUD_DOG__DB__URL", "CLOUD_DOG_DB__URL", "FILE_MCP_DB_URL"
    )
    if explicit_url:
        return DatabaseSettings(url=explicit_url)

    payload: dict[str, Any] = {}
    env_map = {
        "dialect": ("CLOUD_DOG_DB__DIALECT", "CLOUD_DOG__DB__DIALECT"),
        "driver": ("CLOUD_DOG_DB__DRIVER", "CLOUD_DOG__DB__DRIVER"),
        "host": ("CLOUD_DOG_DB__HOST", "CLOUD_DOG__DB__HOST"),
        "port": ("CLOUD_DOG_DB__PORT", "CLOUD_DOG__DB__PORT"),
        "username": ("CLOUD_DOG_DB__USERNAME", "CLOUD_DOG__DB__USERNAME"),
        "password": ("CLOUD_DOG_DB__PASSWORD", "CLOUD_DOG__DB__PASSWORD"),
        "database": ("CLOUD_DOG_DB__DATABASE", "CLOUD_DOG__DB__DATABASE"),
        "path": ("CLOUD_DOG_DB__PATH", "CLOUD_DOG__DB__PATH"),
        "schema_name": ("CLOUD_DOG_DB__SCHEMA", "CLOUD_DOG__DB__SCHEMA"),
    }
    for field, names in env_map.items():
        value = _env_value(*names)
        if value is not None:
            payload[field] = value

    if not payload:
        payload = {
            "dialect": "sqlite",
            "database": _default_sqlite_path(),
        }
    elif (
        not str(payload.get("database") or "").strip()
        and not str(payload.get("url") or "").strip()
    ):
        payload["database"] = _default_sqlite_path()

    return DatabaseSettings.model_validate(payload)


def _sqlite_path(settings: DatabaseSettings) -> Path | None:
    """Handle sqlite path."""
    url = make_url(settings.to_sync_url())
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None
    path_str = url.database
    if not path_utils.is_absolute(path_str):
        path = _project_root() / path_str
    else:
        path = path_utils.as_path(path_str)
    return path


def _migration_script_location() -> str:
    """Handle migration script location."""
    return path_utils.resolve_path(str(_project_root() / "database" / "migrations" / "cloud_dog_db"))


def initialise_database(*, force_reinit: bool = False) -> PlatformDatabaseRuntime:
    """Initialise engine/session/migrations through cloud_dog_db."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None and not force_reinit:
            return _RUNTIME

        settings = _settings_from_env()
        sqlite_path = _sqlite_path(settings)
        if sqlite_path is not None:
            path_utils.mkdir(str(sqlite_path.parent))

        engine = build_sync_engine(settings)
        session_manager = SyncSessionManager(engine)
        runner = MigrationRunner(
            MigrationConfig(
                script_location=_migration_script_location(),
                sqlalchemy_url=settings.to_sync_url(),
            )
        )
        runner.upgrade("head")

        # Ensure any new ORM tables (e.g. FileStorageProfile) exist even
        # when no Alembic migration script has been generated yet.
        from .models import PlatformBase as _ModelBase
        _ModelBase.metadata.create_all(bind=engine, checkfirst=True)

        # W28A-876: ensure the canonical cloud_dog_idam role tables exist so the
        # PS-71 §IW3A Roles page (/api/v1/admin/roles) is backed by the shared
        # SqlAlchemyRoleStore. Only the role-related tables are created here;
        # other idam tables are not part of this service's schema.
        from cloud_dog_idam.storage.sqlalchemy.models import (  # type: ignore[import-not-found,import-untyped]
            PermissionORM as _PermissionORM,
            RoleORM as _RoleORM,
            RolePermissionORM as _RolePermissionORM,
        )
        _RoleORM.metadata.create_all(
            bind=engine,
            checkfirst=True,
            tables=[
                _RoleORM.__table__,
                _PermissionORM.__table__,
                _RolePermissionORM.__table__,
            ],
        )

        _RUNTIME = PlatformDatabaseRuntime(
            settings=settings,
            engine=engine,
            session_manager=session_manager,
            migration_runner=runner,
        )
        return _RUNTIME


def database_health(runtime: PlatformDatabaseRuntime | None = None) -> dict[str, Any]:
    """Return DB probe details for health handlers."""
    active = runtime or _RUNTIME
    if active is None:
        return {"ok": False, "status": "not_initialised"}
    try:
        probe = probe_database(active.engine)
        return {"ok": bool(probe.get("ok", False)), "probe": probe}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def shutdown_database() -> None:
    """Dispose database engine."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            return
        _RUNTIME.engine.dispose()
        _RUNTIME = None
