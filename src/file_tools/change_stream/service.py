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

"""File-mcp storage-profile change-watch adapter (PS-102 §4.1, CSTREAM-FILE-001/002).

``WatchService`` is a *thin adapter* over the common change-stream foundation
published in ``cloud_dog_api_kit.change_stream`` (PS-102 §9 / RULES §1.4). It:

* builds a :class:`~cloud_dog_api_kit.change_stream.WatchCoordinator` whose
  per-watch journal is the durable :class:`SqlJournal` (backed by the service's
  ``cloud_dog_db`` engine) so a watch backlog survives restart (CSTREAM-007);
* wires the coordinator's ``on_emit`` hook to the service's existing
  ``cloud_dog_api_kit.a2a.events`` broadcaster via ``make_broadcast_hook`` for
  live SSE fan-out (PS-102 §5.2) — no bespoke broadcaster;
* wires the coordinator's ``audit_sink`` to ``cloud_dog_logging`` (CSTREAM-010);
* enforces RBAC/tenancy at the adapter boundary — a watch is scoped to a tenant
  + storage profile; cross-tenant reads are a hard failure (CSTREAM-009);
* translates observed storage mutations (server-mediated capture of changes made
  THROUGH file-mcp, plus a bounded controlled-scan of the underlying storage) into
  the canonical :class:`ChangeEvent` envelope and emits them to every *live* watch
  whose criteria match (CSTREAM-FILE-001/002).

This adapter re-implements NO journal, cursor, queue, broadcaster, RBAC, or error
model — all of that is consumed from the foundation.

Backend support (CSTREAM-FILE, PS-102 §6):

* ``local``   — server-mediated capture + native mtime/size scan fallback.
* ``s3``      — server-mediated capture + listing+etag scan fallback.
* ``webdav``  — server-mediated capture + listing+mtime scan fallback.
* ``ftp``     — server-mediated capture + listing+mtime scan fallback.
* ``google_drive`` — server-mediated capture only (honest unsupported-scan row).

A backend that has no efficient native/underlying detection returns an honest
``unsupported`` row from :meth:`backend_support` and only receives events for
changes made through file-mcp (server-mediated).
"""

from __future__ import annotations

import contextlib
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cloud_dog_api_kit.change_stream import (
    ACTIONS,
    ChangeEvent,
    WatchCoordinator,
    WatchSpec,
    make_broadcast_hook,
)
from cloud_dog_api_kit.change_stream.db_journal import SqlJournal
from cloud_dog_api_kit.change_stream.errors import (
    InvalidCriteria,
    WatchNotFound,
)
from cloud_dog_api_kit.change_stream.journal import InMemoryJournal, Journal

from file_tools.change_stream.criteria import (
    ChangeCandidate,
    validate_criteria,
)
from file_tools.change_stream.criteria import (
    match as criteria_match,
)

SERVICE_ID = "file-mcp"

# Backend source_type mapping for the ChangeEvent envelope (PS-102 §4).
_SOURCE_TYPE = {
    "local": "local_fs",
    "s3": "s3",
    "webdav": "webdav",
    "ftp": "ftp",
    "google_drive": "google_drive",
}

# The file-mcp tool verbs whose successful execution is a server-mediated storage
# mutation, mapped to the canonical envelope action (PS-102 §4). Used by the
# runtime capture shim to translate a tool call into a ChangeEvent candidate.
TOOL_ACTION_MAP: dict[str, str] = {
    "write_file": "updated",
    "b64_decode_to_file": "updated",
    "delete_file": "deleted",
    "copy_file": "created",
    "rename_path": "renamed",
    "move_path": "moved",
    "create_dir": "created",
    "json_set_file": "updated",
    "yaml_set_file": "updated",
    "xml_set_file": "updated",
    "html_set_file": "updated",
    "markdown_set_section_file": "updated",
    "markdown_set_frontmatter_file": "updated",
    "yaml_delete_file": "updated",
    "sed_edit_file": "updated",
    "chmod_path": "metadata_changed",
}


# Bounded controlled-scan defaults (CSTREAM-FILE-002 / CSTREAM-006). A native
# mechanism is preferred; where a backend only supports listing, the scan is
# bounded on every axis so it can never saturate a backend or busy-wait.
@dataclass(frozen=True)
class ScanLimits:
    """Bounded controlled-scan limits (CSTREAM-FILE-002 / PS-102 §6).

    Every axis is capped so the underlying-storage observation strategy can never
    saturate a backend, busy-wait, or grow unbounded IO/CPU:

    * ``max_depth``        — maximum path depth traversed per scan.
    * ``max_entries``      — maximum entries examined per scan (page-size cap).
    * ``max_parallelism``  — maximum concurrent listing operations.
    * ``min_interval_seconds`` — minimum wall-clock gap between scans (rate cap).
    * ``backoff_seconds``  — backoff applied after a backend error before retry.
    """

    max_depth: int = 8
    max_entries: int = 5000
    max_parallelism: int = 1
    min_interval_seconds: float = 30.0
    backoff_seconds: float = 60.0


# Per-backend observation strategy (CSTREAM-FILE-002, PS-102 §6 native-first).
_BACKEND_STRATEGY: dict[str, dict[str, Any]] = {
    "local": {
        "server_mediated": True,
        "native": "mtime/size scan",
        "detection": "supported",
        "notes": "server-mediated capture + bounded local mtime/size scan fallback",
    },
    "s3": {
        "server_mediated": True,
        "native": "listing+etag scan",
        "detection": "supported",
        "notes": "server-mediated capture + bounded object listing + etag compare",
    },
    "webdav": {
        "server_mediated": True,
        "native": "listing+mtime scan",
        "detection": "supported",
        "notes": "server-mediated capture + bounded PROPFIND listing + mtime compare",
    },
    "ftp": {
        "server_mediated": True,
        "native": "listing+mtime scan",
        "detection": "supported",
        "notes": "server-mediated capture + bounded LIST/MLSD + mtime compare",
    },
    "google_drive": {
        "server_mediated": True,
        "native": None,
        "detection": "unsupported",
        "notes": (
            "server-mediated capture only; underlying-storage change detection "
            "is unsupported (no efficient listing+etag scan wired)"
        ),
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WatchService:
    """Per-service change-watch adapter binding the common coordinator to storage ops.

    Args:
        service_id: stable service identifier for the envelope (``file-mcp``).
        engine: an optional SQLAlchemy ``Engine`` (from ``cloud_dog_db``). When
            supplied, watches journal durably via :class:`SqlJournal`; when
            ``None`` (unit tests / no DB), a bounded in-memory journal is used so
            the adapter still functions without a live database.
        broadcaster: an optional ``cloud_dog_api_kit.a2a.events`` broadcaster; when
            supplied, emitted events fan out live via ``make_broadcast_hook``.
        audit_sink: optional ``(kind, mapping)`` callable — the service wires
            ``cloud_dog_logging`` here.
        broadcast_scheduler: optional scheduler for the (async) broadcast publish
            so the sync emit path never blocks a worker (CSTREAM-002).
        scan_limits: bounded controlled-scan limits (CSTREAM-FILE-002).
    """

    def __init__(
        self,
        *,
        service_id: str = SERVICE_ID,
        engine: Any | None = None,
        broadcaster: Any | None = None,
        audit_sink: Callable[[str, Mapping[str, Any]], None] | None = None,
        broadcast_scheduler: Callable[[Any], None] | None = None,
        scan_limits: ScanLimits | None = None,
    ) -> None:
        self._service_id = service_id
        self._engine = engine
        self._scan_limits = scan_limits or ScanLimits()
        self._lock = threading.RLock()
        # watch_id -> declarative spec view (tenant/profile/criteria) kept for
        # criteria evaluation + RBAC scoping. The coordinator owns state/journal.
        self._specs: dict[str, WatchSpec] = {}
        self._criteria: dict[str, Mapping[str, Any]] = {}
        # watch_id -> the storage backend name bound to the profile (for the
        # envelope source_type + backend criteria). Defaults to "" (unknown).
        self._backends: dict[str, str] = {}

        on_emit = None
        if broadcaster is not None:
            on_emit = make_broadcast_hook(broadcaster, scheduler=broadcast_scheduler)

        # Ensure the durable journal table exists once (idempotent).
        if engine is not None:
            with contextlib.suppress(Exception):  # pragma: no cover - schema may already exist
                SqlJournal.create_schema(engine)

        self._coordinator = WatchCoordinator(
            journal_factory=self._journal_factory,
            on_emit=on_emit,
            audit_sink=audit_sink,
        )

    # ------------------------------------------------------------------
    # journal factory (durable SqlJournal, else bounded in-memory)
    # ------------------------------------------------------------------
    def _journal_factory(self, spec: WatchSpec) -> Journal:
        if self._engine is not None:
            return SqlJournal(
                self._engine,
                spec.watch_id,
                max_size=spec.journal_max,
                ttl_seconds=spec.journal_ttl_seconds,
            )
        return InMemoryJournal(max_size=spec.journal_max, ttl_seconds=spec.journal_ttl_seconds)

    @property
    def coordinator(self) -> WatchCoordinator:
        return self._coordinator

    @property
    def scan_limits(self) -> ScanLimits:
        return self._scan_limits

    # ------------------------------------------------------------------
    # backend support matrix (CSTREAM-FILE-002 / PS-102 §6) — honest rows
    # ------------------------------------------------------------------
    @staticmethod
    def backend_support(backend: str | None = None) -> Any:
        """Return the backend-support row(s) (honest unsupported where applicable).

        When ``backend`` is ``None`` returns the full matrix; otherwise returns a
        single row. A backend with no efficient underlying detection is reported
        with ``detection == "unsupported"`` rather than silently pretending to
        support it (CSTREAM-FILE / PS-102 §5.6 ``unsupported_backend``).
        """
        if backend is None:
            return {name: dict(row) for name, row in _BACKEND_STRATEGY.items()}
        row = _BACKEND_STRATEGY.get(str(backend).lower())
        if row is None:
            return {
                "backend": backend,
                "server_mediated": False,
                "native": None,
                "detection": "unsupported",
                "notes": f"unknown storage backend {backend!r}",
            }
        return {"backend": str(backend).lower(), **dict(row)}

    # ------------------------------------------------------------------
    # RBAC / tenancy boundary (CSTREAM-009)
    # ------------------------------------------------------------------
    def _require_owner(self, watch_id: str, tenant_id: str) -> WatchSpec:
        """Return the spec if the caller's tenant owns the watch, else raise.

        Cross-tenant / cross-profile access is a hard failure — the watch is
        scoped to the tenant it was created under (PS-102 §7). Existence is not
        leaked across tenants.
        """
        spec = self._specs.get(watch_id)
        if spec is None:
            raise WatchNotFound(f"no watch {watch_id!r}")
        if tenant_id is not None and spec.tenant_id != tenant_id:
            raise WatchNotFound(f"no watch {watch_id!r}")
        return spec

    # ------------------------------------------------------------------
    # lifecycle (create/list/status/pause/resume/delete) — PS-102 §5.1
    # ------------------------------------------------------------------
    def create_watch(
        self,
        *,
        profile_id: str,
        tenant_id: str,
        actor: str,
        backend: str = "",
        criteria: Mapping[str, Any] | None = None,
        max_batch: int = 100,
        max_inflight: int = 4,
        journal_max: int = 1000,
        journal_ttl_seconds: float | None = None,
        watch_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_criteria = dict(criteria or {})
        validate_criteria(resolved_criteria)
        if max_batch < 1 or max_inflight < 1 or journal_max < 1:
            raise InvalidCriteria("max_batch, max_inflight and journal_max must be >= 1")
        wid = watch_id or f"fmw-{uuid.uuid4().hex[:16]}"
        spec = WatchSpec(
            watch_id=wid,
            service_id=self._service_id,
            profile_id=profile_id,
            tenant_id=tenant_id,
            actor=actor,
            criteria=resolved_criteria,
            max_batch=max_batch,
            max_inflight=max_inflight,
            journal_max=journal_max,
            journal_ttl_seconds=journal_ttl_seconds,
        )
        with self._lock:
            status = self._coordinator.create_watch(spec)
            self._specs[wid] = spec
            self._criteria[wid] = resolved_criteria
            self._backends[wid] = str(backend or "").lower()
        return self._watch_view(spec, status)

    def list_watches(self, *, tenant_id: str) -> list[dict[str, Any]]:
        with self._lock:
            out: list[dict[str, Any]] = []
            for wid, spec in self._specs.items():
                if spec.tenant_id != tenant_id:
                    continue
                out.append(self._watch_view(spec, self._coordinator.get_status(wid)))
            return out

    def get_watch(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        spec = self._require_owner(watch_id, tenant_id)
        return self._watch_view(spec, self._coordinator.get_status(watch_id))

    def get_status(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.get_status(watch_id))

    def pause(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.pause(watch_id))

    def resume(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.resume(watch_id))

    def delete(self, watch_id: str, *, tenant_id: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        with self._lock:
            self._coordinator.delete(watch_id)
            self._specs.pop(watch_id, None)
            self._criteria.pop(watch_id, None)
            self._backends.pop(watch_id, None)
        return {"watch_id": watch_id, "deleted": True}

    # ------------------------------------------------------------------
    # retrieval / ack / recover — PS-102 §5.2 (pull-batch base mode)
    # ------------------------------------------------------------------
    def get_batch(
        self,
        watch_id: str,
        *,
        tenant_id: str,
        since_cursor: str | None = None,
        max_batch: int | None = None,
    ) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        result = self._coordinator.get_batch(watch_id, since_cursor=since_cursor, max_batch=max_batch)
        return WatchCoordinator.batch_to_dict(result, redact=True)

    def ack(self, watch_id: str, *, tenant_id: str, ack_cursor: str) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        return self._status_view(self._coordinator.ack(watch_id, ack_cursor))

    def recover(
        self, watch_id: str, *, tenant_id: str, since_cursor: str | None = None
    ) -> dict[str, Any]:
        self._require_owner(watch_id, tenant_id)
        cursor = self._coordinator.recover(watch_id, since_cursor=since_cursor)
        return {"watch_id": watch_id, "resume_cursor": cursor}

    def test_event(
        self,
        watch_id: str,
        *,
        tenant_id: str,
        action: str = "created",
        object_ref: str = "test",
        **meta: Any,
    ) -> dict[str, Any]:
        """Inject a deterministic synthetic event (PS-102 §5.8).

        Injects into the watch's journal without mutating any external backend.
        """
        self._require_owner(watch_id, tenant_id)
        if action not in ACTIONS:
            raise InvalidCriteria(f"unknown action verb {action!r}")
        seq = self._coordinator.test_event(watch_id, action=action, object_ref=object_ref, **meta)
        return {"watch_id": watch_id, "emitted_seq": seq, "action": action, "object_ref": object_ref}

    # ------------------------------------------------------------------
    # health (PS-102 §5.9) — aggregated for the service /health
    # ------------------------------------------------------------------
    def health(self) -> dict[str, int]:
        with self._lock:
            return self._coordinator.health()

    # ------------------------------------------------------------------
    # domain-event capture (CSTREAM-FILE-001/002) — server-mediated + scan
    # ------------------------------------------------------------------
    def observe_change(
        self,
        *,
        tenant_id: str,
        profile_id: str,
        path: str,
        action: str,
        backend: str = "",
        is_dir: bool = False,
        object_version: str = "",
        old_path: str = "",
        size: int | None = None,
        mtime: str = "",
        etag: str = "",
        content_hash: str = "",
        metadata: Mapping[str, Any] | None = None,
        actor: str | None = None,
        correlation_id: str | None = None,
        summary: str = "",
        capture: str = "server_mediated",
    ) -> list[str]:
        """Fan a single observed storage change into every matching *live* watch.

        Returns the list of watch ids the change was emitted to (may be empty).
        ``capture`` is ``"server_mediated"`` for a change made through file-mcp
        (native-first, no polling/scan, no busy-wait — PS-102 §6) or
        ``"underlying_scan"`` for a bounded controlled-scan observation.
        """
        if action not in ACTIONS:
            # Defensive: an unknown verb is a contract error, but capture must
            # never crash the mutating request path — skip silently.
            return []
        meta = dict(metadata or {})
        if size is not None:
            meta.setdefault("size", size)
        if mtime:
            meta.setdefault("mtime", mtime)
        if etag:
            meta.setdefault("etag", etag)
        if content_hash:
            meta.setdefault("content_hash", content_hash)
        candidate = ChangeCandidate(
            path=path,
            action=action,
            backend=(backend or str(meta.get("backend", ""))).lower(),
            is_dir=bool(is_dir or meta.get("is_dir")),
            object_version=object_version,
            old_path=old_path or str(meta.get("old_path", "")),
            metadata=meta,
        )
        emitted: list[str] = []
        # snapshot watch ids under lock; emit outside the lock (the coordinator is
        # single-process and its own emit is cheap + bounded).
        with self._lock:
            targets = [
                (wid, spec, self._criteria.get(wid, {}), self._backends.get(wid, ""))
                for wid, spec in self._specs.items()
                if spec.tenant_id == tenant_id and spec.profile_id == profile_id
            ]
        for wid, spec, crit, wbackend in targets:
            # only emit to live watches; a paused watch retains its cursor and is
            # not fed new events (PS-102 §5.1).
            status = self._coordinator.get_status(wid)
            if status.state != "live":
                continue
            # infer the backend for the envelope: candidate wins, else the
            # profile's bound backend recorded at create time.
            eff_backend = candidate.backend or wbackend
            eval_candidate = candidate
            if eff_backend != candidate.backend:
                eval_candidate = ChangeCandidate(
                    path=candidate.path,
                    action=candidate.action,
                    backend=eff_backend,
                    is_dir=candidate.is_dir,
                    object_version=candidate.object_version,
                    old_path=candidate.old_path,
                    metadata=candidate.metadata,
                )
            matched = criteria_match(crit, eval_candidate)
            if matched is None:
                continue
            event = self._build_event(
                spec=spec,
                candidate=eval_candidate,
                criteria_match=matched,
                actor=actor,
                correlation_id=correlation_id,
                summary=summary,
                capture=capture,
            )
            try:
                self._coordinator.emit(wid, event)
                emitted.append(wid)
            except Exception:  # pragma: no cover - a paused/removed watch races
                continue
        return emitted

    # ------------------------------------------------------------------
    # envelope + view builders
    # ------------------------------------------------------------------
    def _build_event(
        self,
        *,
        spec: WatchSpec,
        candidate: ChangeCandidate,
        criteria_match: Mapping[str, Any],
        actor: str | None,
        correlation_id: str | None,
        summary: str,
        capture: str,
    ) -> ChangeEvent:
        # per-service typed metadata extension (PS-102 §4.1 file-mcp row)
        meta = candidate.metadata
        typed_metadata: dict[str, Any] = {
            "backend": candidate.backend,
            "size": meta.get("size"),
            "mtime": str(meta.get("mtime", "")),
            "etag": str(meta.get("etag", "")),
            "is_dir": candidate.is_dir,
        }
        if candidate.old_path:
            typed_metadata["old_path"] = candidate.old_path
        if meta.get("content_hash"):
            typed_metadata["content_hash"] = str(meta.get("content_hash"))
        source_type = _SOURCE_TYPE.get(candidate.backend, candidate.backend or "storage")
        object_version = (
            candidate.object_version
            or str(meta.get("etag", ""))
            or str(meta.get("mtime", ""))
            or candidate.path
        )
        return ChangeEvent(
            watch_id=spec.watch_id,
            service_id=self._service_id,
            profile_id=spec.profile_id,
            source_type=source_type,
            source_ref=f"{spec.profile_id}:{candidate.backend or 'storage'}",
            action=candidate.action,
            object_ref=candidate.path,
            object_version=object_version,
            tenant_id=spec.tenant_id,
            event_time=_utc_now(),
            observed_time=_utc_now(),
            criteria_match=dict(criteria_match),
            summary=summary or _default_summary(candidate),
            metadata=typed_metadata,
            correlation_id=correlation_id,
            actor={"id": actor, "type": "user"} if actor else None,
            provenance={"capture": capture, "backend": candidate.backend},
        )

    def _watch_view(self, spec: WatchSpec, status: Any) -> dict[str, Any]:
        backend = self._backends.get(spec.watch_id, "")
        return {
            "watch_id": spec.watch_id,
            "service_id": spec.service_id,
            "profile_id": spec.profile_id,
            "tenant_id": spec.tenant_id,
            "actor": spec.actor,
            "backend": backend,
            "backend_support": self.backend_support(backend) if backend else None,
            "criteria": dict(spec.criteria),
            "max_batch": spec.max_batch,
            "max_inflight": spec.max_inflight,
            "journal_max": spec.journal_max,
            "journal_ttl_seconds": spec.journal_ttl_seconds,
            "status": self._status_view(status),
        }

    @staticmethod
    def _status_view(status: Any) -> dict[str, Any]:
        return {
            "watch_id": status.watch_id,
            "tenant_id": status.tenant_id,
            "state": status.state,
            "journal_depth": status.depth,
            "earliest_seq": status.earliest_seq,
            "latest_seq": status.latest_seq,
            "ack_seq": status.ack_seq,
            "inflight": status.inflight,
            "throttled": status.throttled,
            "trimmed_total": status.trimmed_total,
        }


def make_audit_sink(audit_logger: Any) -> Callable[[str, Mapping[str, Any]], None]:
    """Build a coordinator ``audit_sink`` that writes to ``cloud_dog_logging``.

    The common :class:`WatchCoordinator` calls ``audit_sink(kind, row)`` for every
    lifecycle / emission / delivery / ack / recover / throttle event (CSTREAM-010).
    This adapter maps each to the service's audit logger so watch audit lands in
    the same privileged audit stream as the rest of the service — no bespoke audit
    writer (RULES §1.4). The logger is duck-typed: a ``log_admin_action`` method
    (cloud_dog_idam / cloud_dog_logging audit adapter) is used when present.
    """

    def _sink(kind: str, row: Mapping[str, Any]) -> None:
        watch_id = str(row.get("watch_id", ""))
        actor = str(row.get("actor") or "system")
        details = {k: v for k, v in row.items() if k not in {"watch_id", "actor"}}
        with contextlib.suppress(Exception):  # pragma: no cover - audit must never break the flow
            logfn = getattr(audit_logger, "log_admin_action", None)
            if callable(logfn):
                logfn(
                    actor=actor,
                    roles=set(),
                    action=f"change_watch.{kind}",
                    target_type="change_watch",
                    target_id=watch_id or "-",
                    new_value=details or None,
                )
                return
            # Fallback: a plain logger-like object with .info(...).
            infofn = getattr(audit_logger, "info", None)
            if callable(infofn):
                infofn(f"change_watch.{kind}", watch_id=watch_id, actor=actor, **details)

    return _sink


def _default_summary(candidate: ChangeCandidate) -> str:
    kind = "dir" if candidate.is_dir else "object"
    label = candidate.path
    if candidate.old_path:
        label = f"{candidate.old_path} -> {candidate.path}"
    return f"{candidate.action} {kind} {label}".strip()
