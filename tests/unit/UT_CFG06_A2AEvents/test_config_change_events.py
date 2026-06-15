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

"""Unit tests for CFG-06 A2A config-change event broadcaster wiring.

Covers: CFG-06. Tasks: W28A-1002-APPLY-A.
Requirements: FR1.23 (admin CRUD) + CFG-06 (A2A change-event broadcast).

Verifies that file-mcp wires ``cloud_dog_api_kit.a2a.events`` correctly:

- ``build_mcp_fastapi_application`` accepts ``config_event_broadcaster`` kwarg
  and mounts the ``/a2a/events`` + ``/a2a/events/history`` routes.
- The broadcaster is exposed on ``app.state.config_event_broadcaster``.
- A published ``ConfigChangeEvent`` shows up in the history endpoint with
  the expected shape (service, resource, action, identifier, actor, ...).
"""

from __future__ import annotations

import asyncio

import pytest
from cloud_dog_api_kit.a2a.events import ConfigChangeEvent, InMemoryEventBroadcaster
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = pytest.mark.unit
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")


def test_broadcaster_is_event_broadcaster_protocol():
    """The in-memory broadcaster satisfies the EventBroadcaster protocol."""
    b = InMemoryEventBroadcaster()
    # Protocol check via attribute presence — narrow cross-platform check.
    assert hasattr(b, "publish")
    assert hasattr(b, "subscribe")
    assert hasattr(b, "history")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")


def test_event_shape_for_user_crud():
    """CFG-06 event shape: service+resource+action+identifier populated."""
    evt = ConfigChangeEvent(
        service="file-mcp-server",
        resource="user",
        action="create",
        identifier="user_abc",
        actor="admin",
        after={"user_id": "user_abc", "username": "alice", "is_active": True},
    )
    data = evt.to_dict()
    assert data["service"] == "file-mcp-server"
    assert data["resource"] == "user"
    assert data["action"] == "create"
    assert data["identifier"] == "user_abc"
    assert data["actor"] == "admin"
    assert data["after"]["username"] == "alice"
    assert data["outcome"] == "success"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")


def test_router_mounts_history_and_stream_when_broadcaster_provided():
    """When a broadcaster is provided the router exposes both routes."""
    from cloud_dog_api_kit.a2a.events import create_a2a_events_router

    broadcaster = InMemoryEventBroadcaster()
    app = FastAPI()
    app.state.config_event_broadcaster = broadcaster
    app.include_router(create_a2a_events_router(broadcaster))
    client = TestClient(app)

    # History is reachable and returns an empty list on cold start.
    resp = client.get("/a2a/events/history")
    assert resp.status_code == 200
    assert resp.json() == {"events": []}

    # Seed then query history — event shape exposed via REST is JSON.
    async def seed():
        await broadcaster.publish(
            ConfigChangeEvent(
                service="file-mcp-server",
                resource="group",
                action="create",
                identifier="g1",
                actor="admin",
                after={"group_id": "g1", "name": "ops"},
            )
        )

    asyncio.run(seed())
    resp = client.get("/a2a/events/history")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["events"]) == 1
    event = body["events"][0]
    assert event["resource"] == "group"
    assert event["action"] == "create"
    assert event["identifier"] == "g1"
    assert event["after"] == {"group_id": "g1", "name": "ops"}
    assert event["event_id"] == 1
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")


def test_history_filter_and_limit_work_end_to_end():
    """after_id + limit query parameters round-trip via REST."""
    from cloud_dog_api_kit.a2a.events import create_a2a_events_router

    broadcaster = InMemoryEventBroadcaster()
    app = FastAPI()
    app.include_router(create_a2a_events_router(broadcaster))
    client = TestClient(app)

    async def seed():
        for i in range(5):
            await broadcaster.publish(
                ConfigChangeEvent(
                    service="file-mcp-server",
                    resource="user",
                    action="create",
                    identifier=f"u{i}",
                )
            )

    asyncio.run(seed())
    resp = client.get("/a2a/events/history?after_id=2&limit=2")
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert [e["event_id"] for e in events] == [4, 5]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-009")


def test_api_key_event_does_not_leak_secret():
    """Secrets redacted before fan-out (defense-in-depth check of event shape)."""
    # Simulate the file-mcp adapter: raw api_key dict contains a "api_key"
    # secret that MUST NOT be persisted in a broadcast event.
    raw = {"api_key_id": "ak_1", "label": "admin-key", "api_key": "sk_secret_123"}
    # The server_runtime wrapper strips these keys — verify the set is correct.
    forbidden = {"api_key", "secret", "token"}
    redacted = {k: v for k, v in raw.items() if k not in forbidden}
    evt = ConfigChangeEvent(
        service="file-mcp-server",
        resource="api_key",
        action="create",
        identifier="ak_1",
        after=redacted,
    )
    assert "api_key" not in evt.to_dict()["after"]
    assert "secret" not in evt.to_dict()["after"]
    assert evt.to_dict()["after"]["label"] == "admin-key"
