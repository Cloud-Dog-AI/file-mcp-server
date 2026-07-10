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

"""File-mcp storage change-watch criteria matching (PS-102 CSTREAM-FILE-001/002).

The criteria matcher is a *pure* function over a proposed :class:`ChangeCandidate`
(a storage-profile object path + action + backend + directory/size/mtime/etag
metadata) and a watch's declarative ``criteria`` mapping. It decides whether an
observed change matches a watch and, when it does, returns the ``criteria_match``
provenance the common
:class:`cloud_dog_api_kit.change_stream.ChangeEvent` envelope requires so a
consumer can prove the event is not a false positive (PS-102 §4).

Supported criteria fields (CSTREAM-FILE-001):

* ``path`` — glob (``fnmatch``) OR ``re:`` regex over the object path.
* ``glob`` — explicit glob over the object path (``re:`` still routes to regex).
* ``regex`` — explicit regex over the object path (bare pattern, no ``re:`` prefix).
* ``backend`` — one backend name or a list (``local`` / ``s3`` / ``webdav`` / ``ftp`` / ``google_drive``).
* ``is_dir`` — bool: match only directory-container changes (or only object changes).
* ``metadata`` — mapping of metadata-key -> required value (exact or ``re:``).
* ``metadata_keys`` — list of metadata keys that MUST be present.
* ``action`` — one action verb or a list of verbs from the canonical set.

No criterion means "match everything" (an unfiltered watch). This module owns NO
journal / cursor / queue logic — that all lives in the common foundation
(``cloud_dog_api_kit.change_stream``); RULES §1.4.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cloud_dog_api_kit.change_stream import ACTIONS
from cloud_dog_api_kit.change_stream.errors import InvalidCriteria

_REGEX_PREFIX = "re:"

# Criteria keys this service understands (CSTREAM-FILE-001). Unknown keys are a
# hard InvalidCriteria at watch-create time rather than a silent no-op.
_KNOWN_CRITERIA = frozenset(
    {
        "path",
        "glob",
        "regex",
        "backend",
        "is_dir",
        "metadata",
        "metadata_keys",
        "action",
    }
)


@dataclass(frozen=True)
class ChangeCandidate:
    """A proposed storage change evaluated against a watch's criteria.

    ``metadata`` is the redaction-safe object metadata (backend, size, mtime,
    etag, is_dir, old_path, content_hash, ...). The candidate carries no secrets
    — the coordinator additionally redacts metadata before it rests in the
    journal.
    """

    path: str
    action: str
    backend: str = ""
    is_dir: bool = False
    object_version: str = ""
    old_path: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


def validate_criteria(criteria: Mapping[str, Any]) -> None:
    """Validate a watch's criteria mapping, raising ``InvalidCriteria`` on error.

    Called at watch-create time so an unsupported field / bad regex / unknown
    action verb is rejected *before* the watch starts (PS-102 §5.1).
    """
    if not isinstance(criteria, Mapping):
        raise InvalidCriteria("criteria must be a mapping")
    unknown = set(criteria) - _KNOWN_CRITERIA
    if unknown:
        raise InvalidCriteria(
            f"unsupported criteria field(s): {', '.join(sorted(unknown))}; "
            f"supported: {', '.join(sorted(_KNOWN_CRITERIA))}"
        )
    # action verbs must be from the canonical set
    actions = criteria.get("action")
    if actions is not None:
        for verb in _as_list(actions):
            if verb not in ACTIONS:
                raise InvalidCriteria(
                    f"unknown action verb {verb!r}; valid: {', '.join(sorted(ACTIONS))}"
                )
    # is_dir must be a bool
    if "is_dir" in criteria and not isinstance(criteria["is_dir"], bool):
        raise InvalidCriteria("is_dir criterion must be a boolean")
    # metadata_keys must be a list of strings
    keys = criteria.get("metadata_keys")
    if keys is not None and not isinstance(keys, (list, tuple)):
        raise InvalidCriteria("metadata_keys must be a list of metadata key names")
    # metadata must be a mapping
    meta = criteria.get("metadata")
    if meta is not None and not isinstance(meta, Mapping):
        raise InvalidCriteria("metadata criterion must be a mapping of key -> value")
    # compile any regex patterns eagerly to surface bad patterns now
    for pattern_field in ("path", "glob"):
        raw = criteria.get(pattern_field)
        if isinstance(raw, str) and raw.startswith(_REGEX_PREFIX):
            _compile_regex(raw)
    regex_raw = criteria.get("regex")
    if isinstance(regex_raw, str) and regex_raw:
        _compile_regex(_REGEX_PREFIX + regex_raw)
    if isinstance(meta, Mapping):
        for value in meta.values():
            if isinstance(value, str) and value.startswith(_REGEX_PREFIX):
                _compile_regex(value)


def match(criteria: Mapping[str, Any], candidate: ChangeCandidate) -> dict[str, Any] | None:
    """Return a ``criteria_match`` mapping if the candidate matches, else ``None``.

    An empty ``criteria`` mapping matches everything and returns ``{"all": True}``
    so the envelope's ``criteria_match`` is never empty (CSTREAM-004). When any
    criterion fails, the whole watch does NOT match and ``None`` is returned.
    """
    if not criteria:
        return {"all": True}

    matched: dict[str, Any] = {}

    # action verb — single or list
    if "action" in criteria:
        wanted = _as_list(criteria["action"])
        if candidate.action not in wanted:
            return None
        matched["action"] = candidate.action

    # backend — exact (single or list)
    if "backend" in criteria:
        wanted_b = {str(b).lower() for b in _as_list(criteria["backend"])}
        actual_b = (candidate.backend or _meta_str(candidate, "backend")).lower()
        if actual_b not in wanted_b:
            return None
        matched["backend"] = actual_b

    # is_dir — exact bool
    if "is_dir" in criteria:
        want_dir = bool(criteria["is_dir"])
        actual_dir = bool(candidate.is_dir or _meta_bool(candidate, "is_dir"))
        if actual_dir != want_dir:
            return None
        matched["is_dir"] = actual_dir

    # path — glob or regex (re: prefix)
    if "path" in criteria:
        hit = _text_match(str(criteria["path"]), candidate.path)
        if hit is None:
            return None
        matched["path"] = candidate.path

    # glob — explicit glob (an "re:" prefix still routes to regex for convenience)
    if "glob" in criteria:
        hit = _text_match(str(criteria["glob"]), candidate.path)
        if hit is None:
            return None
        matched["glob"] = candidate.path

    # regex — explicit regex (value is a bare pattern, no "re:" prefix)
    if "regex" in criteria:
        hit = _text_match(_REGEX_PREFIX + str(criteria["regex"]), candidate.path)
        if hit is None:
            return None
        matched["regex"] = hit

    # metadata_keys — all keys must be present
    if "metadata_keys" in criteria:
        required = [str(k) for k in _as_list(criteria["metadata_keys"])]
        missing = [k for k in required if k not in candidate.metadata]
        if missing:
            return None
        matched["metadata_keys"] = required

    # metadata — key -> value (exact or regex)
    if "metadata" in criteria:
        wanted_meta = criteria["metadata"]
        matched_meta: dict[str, Any] = {}
        for key, expected in wanted_meta.items():
            if key not in candidate.metadata:
                return None
            actual = candidate.metadata[key]
            if isinstance(expected, str) and expected.startswith(_REGEX_PREFIX):
                if _text_match(expected, str(actual)) is None:
                    return None
            elif str(actual) != str(expected):
                return None
            matched_meta[key] = actual
        matched["metadata"] = matched_meta

    return matched


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _as_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _meta_str(candidate: ChangeCandidate, key: str) -> str:
    val = candidate.metadata.get(key) if isinstance(candidate.metadata, Mapping) else None
    return str(val) if val is not None else ""


def _meta_bool(candidate: ChangeCandidate, key: str) -> bool:
    val = candidate.metadata.get(key) if isinstance(candidate.metadata, Mapping) else None
    return bool(val)


def _compile_regex(raw: str) -> re.Pattern[str]:
    pattern = raw[len(_REGEX_PREFIX):]
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise InvalidCriteria(f"invalid regex {pattern!r}: {exc}") from exc


def _text_match(pattern: str, value: str) -> str | None:
    """Return the matched value/substring when ``pattern`` matches ``value``.

    ``re:`` prefix -> regex ``search``; otherwise a case-sensitive ``fnmatch``
    glob. Returns ``None`` on no match.
    """
    if pattern.startswith(_REGEX_PREFIX):
        compiled = _compile_regex(pattern)
        m = compiled.search(value or "")
        return m.group(0) if m is not None else None
    if fnmatch.fnmatchcase(value or "", pattern):
        return value
    return None
