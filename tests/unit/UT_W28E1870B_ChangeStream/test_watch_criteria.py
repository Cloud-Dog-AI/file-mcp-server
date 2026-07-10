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

"""W28E-1870-B unit tests for the file-mcp storage change-watch criteria matcher.

Covers CSTREAM-FILE-001 (glob/regex over path, action, backend, is_dir, metadata)
and CST-U-* (criteria parsing + envelope criteria_match provenance).
"""

from __future__ import annotations

import pytest
from cloud_dog_api_kit.change_stream.errors import InvalidCriteria

from file_tools.change_stream.criteria import (
    ChangeCandidate,
    match,
    validate_criteria,
)

pytestmark = [pytest.mark.UT, pytest.mark.internal]


def _cand(**kw):
    kw.setdefault("action", "created")
    return ChangeCandidate(**kw)


@pytest.mark.req("CSTREAM-FILE-001")
def test_empty_criteria_matches_everything():
    m = match({}, _cand(path="anything.txt"))
    assert m == {"all": True}


@pytest.mark.req("CSTREAM-FILE-001")
def test_glob_path_criterion():
    # fnmatch semantics (parity with the foundation reference matcher): "*"
    # crosses "/", so "docs/*.md" matches any .md under docs/ recursively.
    # Callers wanting a single path segment use a re: regex (see below).
    crit = {"path": "docs/*.md"}
    assert match(crit, _cand(path="docs/readme.md")) is not None
    assert match(crit, _cand(path="docs/deep/readme.md")) is not None
    assert match(crit, _cand(path="images/a.png")) is None
    # single-segment match via regex when "/" must NOT be crossed
    single = {"path": r"re:^docs/[^/]+\.md$"}
    assert match(single, _cand(path="docs/readme.md")) is not None
    assert match(single, _cand(path="docs/deep/readme.md")) is None


@pytest.mark.req("CSTREAM-FILE-001")
def test_regex_path_via_re_prefix_and_explicit_regex_key():
    assert match({"path": "re:^src/.*\\.py$"}, _cand(path="src/app.py")) is not None
    assert match({"path": "re:^src/.*\\.py$"}, _cand(path="src/app.txt")) is None
    # explicit regex key uses a bare pattern (no re: prefix)
    m = match({"regex": r"\.ya?ml$"}, _cand(path="config/app.yaml"))
    assert m is not None and m["regex"] == ".yaml"
    assert match({"regex": r"\.ya?ml$"}, _cand(path="config/app.json")) is None


@pytest.mark.req("CSTREAM-FILE-001")
def test_action_backend_is_dir_criteria():
    crit = {"action": ["created", "deleted"], "backend": ["s3", "local"], "is_dir": False}
    assert match(crit, _cand(path="a", action="created", backend="s3", is_dir=False)) is not None
    # wrong action
    assert match(crit, _cand(path="a", action="updated", backend="s3")) is None
    # wrong backend
    assert match(crit, _cand(path="a", action="created", backend="ftp")) is None
    # is_dir mismatch
    assert match(crit, _cand(path="a", action="created", backend="s3", is_dir=True)) is None


@pytest.mark.req("CSTREAM-FILE-001")
def test_metadata_and_metadata_keys_criteria():
    cand = _cand(path="a.txt", metadata={"etag": "abc123", "size": 42})
    assert match({"metadata_keys": ["etag"]}, cand) is not None
    assert match({"metadata_keys": ["missing"]}, cand) is None
    assert match({"metadata": {"etag": "abc123"}}, cand) is not None
    assert match({"metadata": {"etag": "re:^abc"}}, cand) is not None
    assert match({"metadata": {"etag": "nope"}}, cand) is None


@pytest.mark.req("CSTREAM-FILE-001")
def test_criteria_match_is_all_or_nothing():
    # one failing criterion fails the whole watch
    crit = {"path": "docs/*.md", "action": ["created"]}
    assert match(crit, _cand(path="docs/x.md", action="deleted")) is None


@pytest.mark.req("CSTREAM-FILE-001")
def test_validate_rejects_unknown_field_and_bad_regex_and_bad_action():
    with pytest.raises(InvalidCriteria):
        validate_criteria({"not_a_field": 1})
    with pytest.raises(InvalidCriteria):
        validate_criteria({"path": "re:[unclosed"})
    with pytest.raises(InvalidCriteria):
        validate_criteria({"action": "no_such_verb"})
    with pytest.raises(InvalidCriteria):
        validate_criteria({"is_dir": "yes"})
    # valid criteria pass
    validate_criteria({"path": "docs/*", "action": ["created", "deleted"], "backend": "s3"})
