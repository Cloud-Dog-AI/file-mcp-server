# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from __future__ import annotations

import pytest

from file_mcp_server.server_runtime import HealthCheckMiddleware


@pytest.mark.UT
@pytest.mark.api
@pytest.mark.req("FR-012")
@pytest.mark.req("FR-017")
def test_rest_file_id_round_trips_absolute_scoped_path() -> None:
    path = "/workspace/profile-a/report.txt"

    file_id = HealthCheckMiddleware._rest_file_id(path)

    assert "/" not in file_id
    assert HealthCheckMiddleware._rest_file_path_from_id(file_id) == path


@pytest.mark.UT
@pytest.mark.api
@pytest.mark.req("CS-002")
@pytest.mark.req("FR-017")
def test_rest_file_scope_allows_read_but_denies_write_for_read_only_profile() -> None:
    read_only_scopes = {"profile:default:read", "files.read"}

    assert HealthCheckMiddleware._rest_file_scope_allows(
        required="files.read",
        scopes=read_only_scopes,
        profile_name="default",
    )
    assert not HealthCheckMiddleware._rest_file_scope_allows(
        required="files.write",
        scopes=read_only_scopes,
        profile_name="default",
    )
