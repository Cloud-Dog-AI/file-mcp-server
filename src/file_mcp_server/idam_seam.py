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

"""file-mcp-server — IDAM keystone seam (W28A-742).

License: Apache 2.0

The seam between the shared ``cloud_dog_idam`` 0.5.0 keystone and file-mcp's
service-local identity storage. See ``IDAM-B2-IDENTITY-DOMAIN-WIRING-DESIGN``
§2.2/§4.1 and the W28A-742 comparison map §3.2/§3.3/§3.5.

Two seam adapters live here:

1. :class:`FileMcpMembershipResolver` — implements the
   :class:`cloud_dog_idam.rbac.membership.MembershipResolver` Protocol over
   file-mcp's own ``FileAdminGroupMember`` table. File-mcp keeps its
   service-local identity storage; the Protocol is the cross-service seam.

2. :func:`build_binding_repo` — returns a
   :class:`cloud_dog_idam.storage.sqlalchemy.repositories.RBACBindingRepository`
   bound to file-mcp's session manager so the ``/idam/v1/rbac/bindings``
   handlers (``server_runtime.py``) persist to the ``rbac_bindings`` table
   created at startup by ``db/runtime.py``.

No bespoke RBAC logic here — both adapters are thin wrappers over the
existing surfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cloud_dog_idam.storage.sqlalchemy.repositories import (
    RBACBindingRepository as _RBACBindingRepository,
)

from .db.models import FileAdminGroupMember

if TYPE_CHECKING:
    from cloud_dog_db import SyncSessionManager


class FileMcpMembershipResolver:
    """File-mcp-local :class:`MembershipResolver` over ``FileAdminGroupMember``.

    The Protocol is one method (``groups_of(user_id) -> set[str]``); the engine
    cache (``grants:{uid}``) handles caching, and W28A-741's extension of
    ``RBACEngine._invalidate_user`` drops that key on add/remove-member so
    revocation lands within one request with no restart (the cascade STEP 5
    proof in ``IDAM-B2 §4.3``).
    """

    def __init__(self, *, session_manager: SyncSessionManager) -> None:
        self._session_manager = session_manager

    def groups_of(self, user_id: str) -> set[str]:
        """Return the set of ``group_id`` values ``user_id`` is currently a member of."""
        with self._session_manager.session() as session:
            rows = (
                session.query(FileAdminGroupMember.group_id)
                .filter(FileAdminGroupMember.user_id == user_id)
                .all()
            )
            return {row[0] for row in rows}


def build_binding_repo(session_or_manager: Any) -> _RBACBindingRepository:
    """Build an ``RBACBindingRepository`` over a file-mcp session.

    The 0.5.0 ``RBACBindingRepository`` takes a SQLAlchemy ``Session`` directly.
    File-mcp's request-handling pattern is ``with session_manager.session() as
    session:`` — so the per-request handler opens its own session and constructs
    the repo around it, scoping persistence to the current transaction.

    Accepts either a session (used by per-request handlers) or a session
    manager (used by tests / boot-time wiring that prefer to construct on
    demand). Manager form delegates back into ``session()``.
    """
    if hasattr(session_or_manager, "session") and callable(
        getattr(session_or_manager, "session")
    ):
        # session_manager form — open a session for the caller. Callers MUST
        # close it; intended for tests / bootstrap, NOT per-request handlers.
        with session_or_manager.session() as session:
            return _RBACBindingRepository(session)
    return _RBACBindingRepository(session_or_manager)


__all__ = [
    "FileMcpMembershipResolver",
    "build_binding_repo",
]
