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

"""Unit coverage for admin identity CRUD service.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Verifies user/group/API-key CRUD and dynamic key resolution behaviour.
Requirements: FR1.36, FR1.46
Tasks: W28A-245
Architecture: 4.1 Authentication
Tests: UT1.30
"""


from __future__ import annotations
import pytest

from pathlib import Path

from file_mcp_server.admin_identity import AdminIdentityService
from file_mcp_server.db.runtime import initialise_database, shutdown_database


def _configure_sqlite_env(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("CLOUD_DOG__DB__DIALECT", "sqlite")
    monkeypatch.setenv("CLOUD_DOG__DB__DATABASE", str(db_path))
    monkeypatch.delenv("CLOUD_DOG__DB__URL", raising=False)
    monkeypatch.delenv("CLOUD_DOG_DB__URL", raising=False)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-016")


def test_create_group_user_and_dynamic_api_key_resolution(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "file-mcp-admin-identity.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    service = AdminIdentityService(session_manager=runtime.session_manager)
    try:
        group = service.create_group(name="admins", roles=["admin"])
        user = service.create_user(
            username="alice",
            display_name="Alice",
            groups=[group["name"]],
        )
        api_key = service.create_api_key(
            user_id=user["id"],
            label="alice-admin",
            scopes=["profile:default"],
        )

        principal = service.resolve_dynamic_api_key(
            token=str(api_key["secret"]),
            profile_name="default",
        )

        assert principal is not None
        assert principal.user_id == user["id"]
        assert principal.role == "admin"
        assert "*" in set(principal.permissions)
        assert "profile:default" in set(principal.permissions)
    finally:
        shutdown_database()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-016")


def test_revoke_api_key_blocks_future_resolution(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "file-mcp-admin-identity-revoke.db"
    _configure_sqlite_env(monkeypatch, db_path)

    runtime = initialise_database(force_reinit=True)
    service = AdminIdentityService(session_manager=runtime.session_manager)
    try:
        user = service.create_user(username="bob")
        api_key = service.create_api_key(
            user_id=user["id"],
            label="bob-key",
            scopes=["profile:default"],
        )

        before = service.resolve_dynamic_api_key(
            token=str(api_key["secret"]),
            profile_name="default",
        )
        assert before is not None

        service.revoke_api_key(str(api_key["id"]))

        after = service.resolve_dynamic_api_key(
            token=str(api_key["secret"]),
            profile_name="default",
        )
        assert after is None
    finally:
        shutdown_database()
