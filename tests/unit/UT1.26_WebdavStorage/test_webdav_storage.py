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

"""WebDAV backend unit tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Validate MOVE retry/backoff behavior for transient WebDAV failures.
"""

from __future__ import annotations

import pytest
import requests

from file_tools.config.models import StorageConfig
from file_tools.storage.webdav import WebDavStorage, _parse_retry_statuses


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


def _storage() -> WebDavStorage:
    return WebDavStorage(
        StorageConfig(
            backend="webdav",
            webdav={
                "base_url": "https://example.test/dav/files/u/root",
                "username": "u",
                "password": "p",
            },
        )
    )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_webdav_move_retries_transient_then_succeeds(monkeypatch) -> None:
    storage = _storage()
    calls: list[int] = []
    seq = [_Resp(500), _Resp(201)]

    def _fake_request(method, url, **kwargs):
        assert method == "MOVE"
        calls.append(1)
        return seq.pop(0)

    monkeypatch.setattr(storage, "_request", _fake_request)
    monkeypatch.setattr(storage, "_path_exists", lambda path: True)
    monkeypatch.setattr("file_tools.storage.webdav.time.sleep", lambda _: None)
    storage.move_path("/a.txt", "/b.txt", overwrite=True)
    assert len(calls) == 2
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_webdav_move_treats_already_applied_as_success(monkeypatch) -> None:
    storage = _storage()

    def _fake_request(method, url, **kwargs):
        return _Resp(500)

    monkeypatch.setattr(storage, "_request", _fake_request)

    def _path_exists(path: str) -> bool:
        return path == "/b.txt"

    monkeypatch.setattr(storage, "_path_exists", _path_exists)
    storage.move_path("/a.txt", "/b.txt", overwrite=True)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_webdav_move_non_transient_raises(monkeypatch) -> None:
    storage = _storage()

    def _fake_request(method, url, **kwargs):
        return _Resp(400)

    monkeypatch.setattr(storage, "_request", _fake_request)
    monkeypatch.setattr("file_tools.storage.webdav.time.sleep", lambda _: None)
    with pytest.raises(requests.HTTPError):
        storage.move_path("/a.txt", "/b.txt", overwrite=True)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_webdav_retry_config_is_read_from_storage_model() -> None:
    storage = WebDavStorage(
        StorageConfig(
            backend="webdav",
            webdav={
                "base_url": "https://example.test/dav/files/u/root",
                "username": "u",
                "password": "p",
                "move_retry_count": "4",
                "move_retry_backoff_s": "0.2",
                "move_probe_timeout_s": "1.5",
                "move_retry_statuses": "500,503, 429",
            },
        )
    )
    assert storage._move_retry_count == 4
    assert storage._move_retry_backoff_s == 0.2
    assert storage._move_probe_timeout_s == 1.5
    assert storage._move_retry_statuses == {429, 500, 503}
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-026")


def test_parse_retry_statuses_falls_back_for_invalid_input() -> None:
    assert _parse_retry_statuses("${FILE_MCP_WEBDAV_MOVE_RETRY_STATUSES}") == {
        408,
        409,
        423,
        425,
        429,
        500,
        502,
        503,
        504,
    }
    assert _parse_retry_statuses("abc,700") == {
        408,
        409,
        423,
        425,
        429,
        500,
        502,
        503,
        504,
    }
