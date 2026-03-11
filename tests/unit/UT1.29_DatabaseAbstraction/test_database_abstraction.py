from __future__ import annotations

from pathlib import Path

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
