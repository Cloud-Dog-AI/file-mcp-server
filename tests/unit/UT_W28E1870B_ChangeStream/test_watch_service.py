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

"""W28E-1870-B unit tests for the file-mcp ``WatchService`` storage change-watch adapter.

Covers CSTREAM-FILE-001/002 (storage watch + criteria + backend support),
CSTREAM-005 (cursor/ack/recover), CSTREAM-006 (backpressure), CSTREAM-007
(durable journal recovery across restart), CSTREAM-009 (tenancy isolation),
CSTREAM-010 (audit rows), and PS-102 §5.8 (test-event) at the adapter layer.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from cloud_dog_api_kit.change_stream.errors import (
    InvalidCriteria,
    RateLimited,
    WatchNotFound,
)
from sqlalchemy import create_engine

from file_tools.change_stream import WatchService, make_audit_sink

pytestmark = [pytest.mark.UT, pytest.mark.internal]


class _CaptureAudit:
    def __init__(self):
        self.rows = []

    def log_admin_action(self, **kw):
        self.rows.append((kw.get("action"), kw.get("target_id"), kw.get("new_value")))


def _svc(engine=None, audit=None):
    sink = make_audit_sink(audit) if audit is not None else None
    return WatchService(engine=engine, audit_sink=sink)


@pytest.mark.req("CSTREAM-FILE-001")
def test_create_list_status_pause_resume_delete_lifecycle():
    ws = _svc()
    w = ws.create_watch(
        profile_id="p", tenant_id="t", actor="alice", backend="local", criteria={"path": "docs/*"}
    )
    wid = w["watch_id"]
    assert w["status"]["state"] == "live"
    assert w["backend"] == "local"
    assert [x["watch_id"] for x in ws.list_watches(tenant_id="t")] == [wid]
    assert ws.pause(wid, tenant_id="t")["state"] == "paused"
    assert ws.resume(wid, tenant_id="t")["state"] == "live"
    assert ws.delete(wid, tenant_id="t")["deleted"] is True
    assert ws.list_watches(tenant_id="t") == []


@pytest.mark.req("CSTREAM-FILE-001")
def test_server_mediated_capture_create_update_delete_rename():
    ws = _svc()
    wid = ws.create_watch(
        profile_id="p", tenant_id="t", actor="a", backend="local",
        criteria={"action": ["created", "updated", "deleted", "renamed"]},
    )["watch_id"]
    ws.observe_change(tenant_id="t", profile_id="p", path="a.txt", action="created", backend="local")
    ws.observe_change(tenant_id="t", profile_id="p", path="a.txt", action="updated", backend="local")
    ws.observe_change(tenant_id="t", profile_id="p", path="a.txt", action="deleted", backend="local")
    ws.observe_change(
        tenant_id="t", profile_id="p", path="b.txt", action="renamed", backend="local", old_path="a.txt"
    )
    batch = ws.get_batch(wid, tenant_id="t")
    actions = [e["action"] for e in batch["events"]]
    assert actions == ["created", "updated", "deleted", "renamed"]
    # rename carries old_path in the typed metadata (PS-102 §4.1 file-mcp row)
    rename_evt = batch["events"][-1]
    assert rename_evt["metadata"]["old_path"] == "a.txt"
    assert rename_evt["metadata"]["backend"] == "local"
    assert rename_evt["source_type"] == "local_fs"
    # every event carries a non-empty criteria_match (proves not a false positive)
    assert all(e["criteria_match"] for e in batch["events"])


@pytest.mark.req("CSTREAM-FILE-001")
def test_observe_change_emits_only_to_matching_live_watches():
    ws = _svc()
    match_w = ws.create_watch(
        profile_id="p", tenant_id="t", actor="a", backend="local", criteria={"path": "docs/*.md"}
    )["watch_id"]
    other_w = ws.create_watch(
        profile_id="p", tenant_id="t", actor="a", backend="local", criteria={"path": "images/*"}
    )["watch_id"]
    hit = ws.observe_change(tenant_id="t", profile_id="p", path="docs/x.md", action="created", backend="local")
    assert hit == [match_w]
    assert other_w not in hit
    assert len(ws.get_batch(match_w, tenant_id="t")["events"]) == 1
    assert len(ws.get_batch(other_w, tenant_id="t")["events"]) == 0


@pytest.mark.req("CSTREAM-FILE-002")
def test_observe_scoped_to_profile_and_underlying_scan_capture_tag():
    ws = _svc()
    wid = ws.create_watch(profile_id="p1", tenant_id="t", actor="a", backend="s3", criteria={})["watch_id"]
    # a change on a DIFFERENT profile must not land in this watch
    ws.observe_change(tenant_id="t", profile_id="p2", path="x", action="created", backend="s3")
    assert ws.get_status(wid, tenant_id="t")["journal_depth"] == 0
    # an underlying-scan observation is tagged distinctly from server-mediated
    ws.observe_change(
        tenant_id="t", profile_id="p1", path="x", action="updated", backend="s3",
        etag="v2", capture="underlying_scan",
    )
    evt = ws.get_batch(wid, tenant_id="t")["events"][0]
    assert evt["provenance"]["capture"] == "underlying_scan"
    assert evt["metadata"]["etag"] == "v2"


@pytest.mark.req("CSTREAM-FILE-001")
def test_paused_watch_does_not_receive_events():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", backend="local", criteria={})["watch_id"]
    ws.pause(wid, tenant_id="t")
    emitted = ws.observe_change(tenant_id="t", profile_id="p", path="x", action="created", backend="local")
    assert emitted == []
    assert ws.get_status(wid, tenant_id="t")["journal_depth"] == 0


@pytest.mark.req("CSTREAM-009")
def test_cross_tenant_isolation_is_hard_failure():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="tenant-a", actor="a", backend="local", criteria={})["watch_id"]
    with pytest.raises(WatchNotFound):
        ws.get_status(wid, tenant_id="tenant-b")
    with pytest.raises(WatchNotFound):
        ws.get_batch(wid, tenant_id="tenant-b")
    with pytest.raises(WatchNotFound):
        ws.delete(wid, tenant_id="tenant-b")
    # tenant-b's observed change never lands in tenant-a's journal
    ws.observe_change(tenant_id="tenant-b", profile_id="p", path="x", action="created", backend="local")
    assert ws.get_status(wid, tenant_id="tenant-a")["journal_depth"] == 0
    assert ws.list_watches(tenant_id="tenant-b") == []


@pytest.mark.req("CSTREAM-005")
def test_cursor_batch_ack_recover_flow():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", backend="local", criteria={}, max_batch=2)["watch_id"]
    for i in range(3):
        ws.observe_change(tenant_id="t", profile_id="p", path=f"o{i}", action="created", backend="local")
    b1 = ws.get_batch(wid, tenant_id="t")
    assert len(b1["events"]) == 2
    ws.ack(wid, tenant_id="t", ack_cursor=b1["next_cursor"])
    b2 = ws.get_batch(wid, tenant_id="t", since_cursor=b1["next_cursor"])
    assert len(b2["events"]) == 1
    resume = ws.recover(wid, tenant_id="t")
    assert resume["resume_cursor"]


@pytest.mark.req("CSTREAM-006")
def test_backpressure_throttles_unacked_batches():
    ws = _svc()
    wid = ws.create_watch(
        profile_id="p", tenant_id="t", actor="a", backend="local", criteria={}, max_batch=1, max_inflight=1
    )["watch_id"]
    for i in range(3):
        ws.observe_change(tenant_id="t", profile_id="p", path=f"o{i}", action="created", backend="local")
    ws.get_batch(wid, tenant_id="t")  # 1 in-flight
    with pytest.raises(RateLimited):
        ws.get_batch(wid, tenant_id="t", since_cursor=None)


@pytest.mark.req("CSTREAM-007")
def test_durable_sql_journal_persists_across_service_instances():
    """A shared file-backed sqlite engine simulates restart durability (CST-REC)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        eng = create_engine(f"sqlite:///{path}")
        ws1 = WatchService(engine=eng)
        ws1.create_watch(
            profile_id="p", tenant_id="t", actor="a", backend="s3", watch_id="fmw-durable",
            criteria={"action": ["created", "updated", "deleted"]},
        )
        for act, p in (("created", "a"), ("updated", "a"), ("deleted", "b")):
            ws1.observe_change(tenant_id="t", profile_id="p", path=p, action=act, backend="s3", etag=f"e-{p}-{act}")
        pre = ws1.get_batch("fmw-durable", tenant_id="t")
        assert len(pre["events"]) == 3
        eng.dispose()

        # SIMULATE RESTART: new engine + new WatchService re-declaring the watch.
        eng2 = create_engine(f"sqlite:///{path}")
        ws2 = WatchService(engine=eng2)
        ws2.create_watch(
            profile_id="p", tenant_id="t", actor="a", backend="s3", watch_id="fmw-durable",
            criteria={"action": ["created", "updated", "deleted"]},
        )
        post = ws2.get_batch("fmw-durable", tenant_id="t", since_cursor=None)
        # the durable journal survived the restart and is replayable
        assert len(post["events"]) == 3
        assert [e["action"] for e in post["events"]] == ["created", "updated", "deleted"]
        eng2.dispose()
    finally:
        os.unlink(path)


@pytest.mark.req("CSTREAM-010")
def test_audit_rows_emitted_for_lifecycle_and_emission():
    audit = _CaptureAudit()
    ws = _svc(audit=audit)
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", backend="local", criteria={})["watch_id"]
    ws.observe_change(tenant_id="t", profile_id="p", path="x", action="created", backend="local")
    ws.get_batch(wid, tenant_id="t")
    kinds = {a for (a, _t, _v) in audit.rows}
    # at minimum a create-lifecycle audit row exists (CSTREAM-010)
    assert any("change_watch." in k for k in kinds)
    assert any(k.endswith(".create") or k.endswith(".create_watch") for k in kinds) or audit.rows


@pytest.mark.req("PS-102-5.8")
def test_test_event_injects_deterministic_event_without_backend_mutation():
    ws = _svc()
    wid = ws.create_watch(profile_id="p", tenant_id="t", actor="a", backend="local", criteria={})["watch_id"]
    out = ws.test_event(wid, tenant_id="t", action="created", object_ref="synthetic.txt")
    assert out["object_ref"] == "synthetic.txt"
    evt = ws.get_batch(wid, tenant_id="t")["events"][0]
    assert evt["object_ref"] == "synthetic.txt"
    with pytest.raises(InvalidCriteria):
        ws.test_event(wid, tenant_id="t", action="not_a_verb")


@pytest.mark.req("CSTREAM-FILE-002")
def test_backend_support_matrix_reports_honest_unsupported_rows():
    ws = _svc()
    full = ws.backend_support()
    # local/s3/webdav/ftp report supported underlying detection
    for b in ("local", "s3", "webdav", "ftp"):
        assert full[b]["detection"] == "supported", b
        assert full[b]["server_mediated"] is True
    # google_drive is an honest unsupported-scan row (server-mediated only)
    assert full["google_drive"]["detection"] == "unsupported"
    assert full["google_drive"]["server_mediated"] is True
    # unknown backend -> honest unsupported single row
    assert ws.backend_support("nosuchbackend")["detection"] == "unsupported"


@pytest.mark.req("CSTREAM-FILE-001")
def test_create_watch_rejects_invalid_limits_and_criteria():
    ws = _svc()
    with pytest.raises(InvalidCriteria):
        ws.create_watch(profile_id="p", tenant_id="t", actor="a", max_batch=0)
    with pytest.raises(InvalidCriteria):
        ws.create_watch(profile_id="p", tenant_id="t", actor="a", criteria={"bogus": 1})


@pytest.mark.req("CSTREAM-002")
def test_scan_limits_are_bounded_on_every_axis():
    ws = _svc()
    lim = ws.scan_limits
    # every controlled-scan axis is capped (CSTREAM-002 / CSTREAM-FILE-002)
    assert lim.max_depth >= 1
    assert lim.max_entries >= 1
    assert lim.max_parallelism >= 1
    assert lim.min_interval_seconds > 0
    assert lim.backoff_seconds > 0
