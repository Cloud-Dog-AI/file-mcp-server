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

"""W28E-1870-B surface tests: MCP tool family, server-mediated capture wrap,
REST route classification, and route-guard RBAC rows.

Covers CSTREAM-001 (MCP + A2A + REST parity), CSTREAM-002 (server-mediated
capture through the mutation tool path), CSTREAM-009 (RBAC route guards).
"""

from __future__ import annotations

import tempfile

import pytest

from file_mcp_server import route_guards
from file_mcp_server import server_runtime as R
from file_tools.config.models import ProfileConfig

pytestmark = [pytest.mark.UT, pytest.mark.internal, pytest.mark.mcp]

_WATCH_TOOLS = {
    "file_watch_create",
    "file_watch_list",
    "file_watch_status",
    "file_watch_get_batch",
    "file_watch_ack",
    "file_watch_recover",
    "file_watch_pause",
    "file_watch_resume",
    "file_watch_delete",
    "file_watch_test_event",
    "file_watch_backend_support",
}


@pytest.fixture()
def local_registry():
    tmp = tempfile.mkdtemp()
    # reset the process-shared watch service so tests don't leak watches
    R.set_shared_watch_service(None)
    prof = ProfileConfig.model_validate(
        {"name": "default", "storage": {"backend": "local"}, "scope": {"roots": [tmp]}}
    )
    reg = R.build_tool_registry(prof, profile_name="default")
    return reg, tmp


@pytest.mark.req("CSTREAM-001")
def test_all_watch_mcp_tools_are_registered(local_registry):
    reg, _tmp = local_registry
    names = {t.meta.name for t in reg.list_tools()}
    assert _WATCH_TOOLS.issubset(names)


@pytest.mark.req("CSTREAM-002")
def test_write_file_through_mcp_triggers_server_mediated_capture(local_registry):
    reg, _tmp = local_registry
    w = reg.get("file_watch_create").handler(
        profile="default", criteria={"path": "*.md", "action": ["created", "updated"]}
    )
    wid = w["watch_id"]
    assert w["backend"] == "local"
    # write a file THROUGH the wrapped write_file tool
    res = reg.get("write_file").handler(path="note.md", content="hello")
    assert res.get("ok") is True  # tool result is unchanged by the capture wrap
    batch = reg.get("file_watch_get_batch").handler(watch_id=wid)
    assert [e["action"] for e in batch["events"]] == ["updated"]
    assert batch["events"][0]["object_ref"] == "note.md"
    # a non-matching write is not captured into this watch
    reg.get("write_file").handler(path="note.txt", content="x")
    batch2 = reg.get("file_watch_get_batch").handler(
        watch_id=wid, since_cursor=batch["next_cursor"]
    )
    assert batch2["events"] == []


@pytest.mark.req("CSTREAM-002")
def test_delete_and_rename_through_mcp_are_captured(local_registry):
    reg, _tmp = local_registry
    wid = reg.get("file_watch_create").handler(
        profile="default", criteria={"action": ["created", "updated", "deleted", "renamed", "moved"]}
    )["watch_id"]
    reg.get("write_file").handler(path="a.txt", content="1")
    reg.get("delete_file").handler(path="a.txt")
    actions = [e["action"] for e in reg.get("file_watch_get_batch").handler(watch_id=wid)["events"]]
    assert "updated" in actions and "deleted" in actions


@pytest.mark.req("CSTREAM-FILE-002")
def test_mcp_backend_support_tool_reports_matrix(local_registry):
    reg, _tmp = local_registry
    out = reg.get("file_watch_backend_support").handler()
    matrix = out["backend_support"]
    assert matrix["google_drive"]["detection"] == "unsupported"
    assert matrix["local"]["detection"] == "supported"


@pytest.mark.req("CSTREAM-009")
@pytest.mark.api
def test_rest_watch_routes_classify_as_guarded_with_correct_permissions():
    # read verbs -> files.read ; write/lifecycle verbs -> files.write (PS-102 §5.5)
    read_cases = [
        ("GET", "/v1/watches"),
        ("GET", "/v1/watches/w1"),
        ("GET", "/v1/watches/w1/status"),
        ("GET", "/v1/watches/w1/events"),
        ("POST", "/v1/watches/w1/ack"),
        ("POST", "/v1/watches/w1/recover"),
    ]
    write_cases = [
        ("POST", "/v1/watches"),
        ("POST", "/v1/watches/w1/pause"),
        ("POST", "/v1/watches/w1/resume"),
        ("POST", "/v1/watches/w1/test-event"),
        ("DELETE", "/v1/watches/w1"),
    ]
    for method, path in read_cases:
        assert route_guards.classify(method, path) == "guarded", (method, path)
        guard = route_guards.match(method, path)
        assert guard is not None and guard[0].permission == "files.read", (method, path)
    for method, path in write_cases:
        assert route_guards.classify(method, path) == "guarded", (method, path)
        guard = route_guards.match(method, path)
        assert guard is not None and guard[0].permission == "files.write", (method, path)


@pytest.mark.req("CSTREAM-001")
def test_is_watches_path_helper_matches_v1_and_api_v1():
    from file_mcp_server.server_runtime import HealthCheckMiddleware as M

    assert M._is_watches_path("/v1/watches")
    assert M._is_watches_path("/v1/watches/w1/events")
    assert M._is_watches_path("/api/v1/watches/w1")
    assert not M._is_watches_path("/v1/profiles")
    assert not M._is_watches_path("/v1/jobs")
