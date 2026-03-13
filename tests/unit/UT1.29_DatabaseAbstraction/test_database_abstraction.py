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

from pathlib import Path

from cloud_dog_db import probe_database

from file_mcp_server.db.models import FilePlatformDbState
from file_mcp_server.db.runtime import (
    database_health,
    initialise_database,
    shutdown_database,
)


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    monkeypatch.delenv("CLOUD_DOG__DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__URL", raising=False)


def test_ut_db_01_engine_factory_creates_sqlite_engine(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "file-mcp-ut.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        assert runtime.engine.url.get_backend_name() == "sqlite"
        health = database_health(runtime)
        assert health["ok"] is True
    finally:
        shutdown_database()


def test_ut_db_02_session_manager_roundtrip(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "file-mcp-ut-roundtrip.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        with runtime.session_manager.session() as session:
            session.add(FilePlatformDbState(service="file-mcp-server", status="ready"))

        with runtime.session_manager.session() as session:
            item = (
                session.query(FilePlatformDbState)
                .filter(FilePlatformDbState.service == "file-mcp-server")
                .one()
            )
            assert item.status == "ready"
    finally:
        shutdown_database()


def test_ut_db_03_probe_database_reports_healthy(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "file-mcp-ut-probe.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    try:
        probe = probe_database(runtime.engine)
        assert bool(probe.get("ok")) is True
    finally:
        shutdown_database()
