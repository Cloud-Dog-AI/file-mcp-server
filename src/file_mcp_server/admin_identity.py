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

"""Admin identity CRUD service for users, groups, and API keys.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Persistent CRUD service for admin user/group/key management and dynamic API-key auth resolution.
Requirements: CFG-08, CFG-09, CFG-10, CFG-11, CFG-12, CFG-13
Tasks: W28A-245
Architecture: 4.1 Authentication
Tests: UT1.30, IT1.26
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import secrets
from typing import Any, Iterable

from cloud_dog_idam.api_keys.hashing import hash_api_key  # type: ignore[import-not-found,import-untyped]
from cloud_dog_logging import get_logger  # type: ignore[import-not-found,import-untyped]

from .db.models import (
    FileAdminApiKey,
    FileAdminGroup,
    FileAdminGroupMember,
    FileAdminUser,
)


class AdminIdentityError(RuntimeError):
    """Structured admin identity error carrying HTTP status and code."""

    def __init__(self, code: str, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class DynamicApiKeyPrincipal:
    """Resolved principal for a dynamically managed API key."""

    api_key_id: str
    user_id: str
    username: str
    role: str
    permissions: tuple[str, ...]
    profile_name: str


def _allows_profile_permission(
    permissions: set[str], profile_name: str
) -> bool:
    """Return True when permissions cover the selected profile."""
    return bool(
        {
            "*",
            "profile:read",
            "profile:write",
            "profile:*",
            f"profile:{profile_name}",
            f"profile:{profile_name}:read",
            f"profile:{profile_name}:write",
        }
        & permissions
    )


class AdminIdentityService:
    """Persistent CRUD service backed by cloud_dog_db session manager."""

    def __init__(self, *, session_manager: Any, logger: Any | None = None) -> None:
        self.session_manager = session_manager
        self.logger = logger or get_logger("file_mcp_server.admin_identity")

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(8)}"

    @staticmethod
    def _parse_json_list(raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        result: list[str] = []
        for item in parsed:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _dump_json_list(values: Iterable[str]) -> str:
        normalised: list[str] = []
        for value in values:
            text = str(value).strip()
            if text and text not in normalised:
                normalised.append(text)
        return json.dumps(normalised, separators=(",", ":"), ensure_ascii=True)

    def _audit(self, *, action: str, outcome: str, details: dict[str, Any]) -> None:
        self.logger.info(
            "admin_identity_audit",
            event="admin_identity_audit",
            action=action,
            outcome=outcome,
            details=details,
        )

    def _user_payload(self, user: FileAdminUser, *, groups: list[str]) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_active": bool(user.is_active),
            "groups": groups,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    def _group_payload(self, group: FileAdminGroup, *, members: list[str]) -> dict[str, Any]:
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "roles": self._parse_json_list(group.roles_json),
            "is_active": bool(group.is_active),
            "members": members,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        }

    @staticmethod
    def _api_key_payload(record: FileAdminApiKey) -> dict[str, Any]:
        return {
            "id": record.id,
            "user_id": record.user_id,
            "label": record.label,
            "scopes": AdminIdentityService._parse_json_list(record.scopes_json),
            "profile_name": record.profile_name,
            "is_active": bool(record.is_active),
            "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def _group_name_by_id(self, session: Any) -> dict[str, str]:
        rows = session.query(FileAdminGroup.id, FileAdminGroup.name).all()
        return {str(group_id): str(name) for group_id, name in rows}

    def _group_members_by_user(self, session: Any) -> dict[str, list[str]]:
        groups = self._group_name_by_id(session)
        rows = session.query(FileAdminGroupMember.user_id, FileAdminGroupMember.group_id).all()
        result: dict[str, list[str]] = {}
        for user_id, group_id in rows:
            uid = str(user_id)
            group_name = groups.get(str(group_id), str(group_id))
            bucket = result.setdefault(uid, [])
            if group_name not in bucket:
                bucket.append(group_name)
        return result

    def _group_members_by_group(self, session: Any) -> dict[str, list[str]]:
        users = {
            str(user_id): str(username)
            for user_id, username in session.query(FileAdminUser.id, FileAdminUser.username).all()
        }
        rows = session.query(FileAdminGroupMember.group_id, FileAdminGroupMember.user_id).all()
        result: dict[str, list[str]] = {}
        for group_id, user_id in rows:
            gid = str(group_id)
            username = users.get(str(user_id), str(user_id))
            bucket = result.setdefault(gid, [])
            if username not in bucket:
                bucket.append(username)
        return result

    def ensure_bootstrap_seed(
        self,
        *,
        username: str = "admin",
        group_name: str = "bootstrap-admin",
    ) -> dict[str, Any]:
        """Ensure the canonical PS-71 bootstrap admin user/group rows exist."""
        clean_username = username.strip() or "admin"
        clean_group_name = group_name.strip() or "bootstrap-admin"
        with self.session_manager.session() as session:
            user = (
                session.query(FileAdminUser)
                .filter(FileAdminUser.username == clean_username)
                .one_or_none()
            )
            if user is None:
                user = FileAdminUser(
                    id=self._new_id("usr"),
                    username=clean_username,
                    display_name=clean_username.title(),
                    is_active=True,
                )
                session.add(user)
                session.flush()

            group = (
                session.query(FileAdminGroup)
                .filter(FileAdminGroup.name == clean_group_name)
                .one_or_none()
            )
            if group is None:
                group = FileAdminGroup(
                    id=self._new_id("grp"),
                    name=clean_group_name,
                    description="Bootstrap administrators",
                    roles_json=self._dump_json_list(["admin"]),
                    is_active=True,
                )
                session.add(group)
                session.flush()
            else:
                roles = self._parse_json_list(group.roles_json)
                if "admin" not in roles:
                    roles.append("admin")
                    group.roles_json = self._dump_json_list(roles)
                group.is_active = True

            membership = (
                session.query(FileAdminGroupMember)
                .filter(
                    FileAdminGroupMember.group_id == group.id,
                    FileAdminGroupMember.user_id == user.id,
                )
                .one_or_none()
            )
            if membership is None:
                session.add(
                    FileAdminGroupMember(
                        group_id=group.id,
                        user_id=user.id,
                    )
                )

            session.flush()
            self._audit(
                action="ensure_bootstrap_seed",
                outcome="ok",
                details={
                    "user_id": user.id,
                    "username": user.username,
                    "group_id": group.id,
                    "group_name": group.name,
                },
            )
            return {
                "user": self._user_payload(user, groups=[group.name]),
                "group": self._group_payload(group, members=[user.username]),
            }

    def list_users(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            memberships = self._group_members_by_user(session)
            users = session.query(FileAdminUser).order_by(FileAdminUser.username.asc()).all()
            return [
                self._user_payload(user, groups=memberships.get(user.id, []))
                for user in users
            ]

    def get_user(self, user_id: str) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user = (
                session.query(FileAdminUser).filter(FileAdminUser.id == user_id).one_or_none()
            )
            if user is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown user: {user_id}", status=404)
            memberships = self._group_members_by_user(session)
            return self._user_payload(user, groups=memberships.get(user.id, []))

    def create_user(
        self,
        *,
        username: str,
        display_name: str = "",
        is_active: bool = True,
        groups: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        clean_username = username.strip()
        if not clean_username:
            raise AdminIdentityError("VALIDATION_ERROR", "username is required")

        with self.session_manager.session() as session:
            exists = (
                session.query(FileAdminUser)
                .filter(FileAdminUser.username == clean_username)
                .one_or_none()
            )
            if exists is not None:
                raise AdminIdentityError(
                    "CONFLICT", f"user already exists: {clean_username}", status=409
                )

            user = FileAdminUser(
                id=self._new_id("usr"),
                username=clean_username,
                display_name=display_name.strip(),
                is_active=bool(is_active),
            )
            session.add(user)
            session.flush()

            group_names = [str(item).strip() for item in (groups or []) if str(item).strip()]
            if group_names:
                available_groups = {
                    str(group.name): str(group.id)
                    for group in session.query(FileAdminGroup)
                    .filter(FileAdminGroup.name.in_(group_names))
                    .all()
                }
                missing = sorted(set(group_names) - set(available_groups.keys()))
                if missing:
                    raise AdminIdentityError(
                        "NOT_FOUND",
                        "unknown groups: " + ", ".join(missing),
                        status=404,
                    )
                for group_name in group_names:
                    session.add(
                        FileAdminGroupMember(
                            group_id=available_groups[group_name],
                            user_id=user.id,
                        )
                    )
            payload = self._user_payload(user, groups=sorted(set(group_names)))
            self._audit(
                action="create_user",
                outcome="ok",
                details={"user_id": user.id, "username": user.username},
            )
            return payload

    def update_user(self, user_id: str, *, data: dict[str, Any]) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user = (
                session.query(FileAdminUser).filter(FileAdminUser.id == user_id).one_or_none()
            )
            if user is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown user: {user_id}", status=404)

            if "display_name" in data:
                user.display_name = str(data.get("display_name") or "").strip()
            if "is_active" in data:
                user.is_active = bool(data.get("is_active"))

            if "groups" in data:
                for membership in (
                    session.query(FileAdminGroupMember)
                    .filter(FileAdminGroupMember.user_id == user.id)
                    .all()
                ):
                    session.delete(membership)
                group_names = [
                    str(item).strip()
                    for item in (data.get("groups") or [])
                    if str(item).strip()
                ]
                available_groups = {
                    str(group.name): str(group.id)
                    for group in session.query(FileAdminGroup)
                    .filter(FileAdminGroup.name.in_(group_names))
                    .all()
                }
                missing = sorted(set(group_names) - set(available_groups.keys()))
                if missing:
                    raise AdminIdentityError(
                        "NOT_FOUND",
                        "unknown groups: " + ", ".join(missing),
                        status=404,
                    )
                for group_name in group_names:
                    session.add(
                        FileAdminGroupMember(
                            group_id=available_groups[group_name],
                            user_id=user.id,
                        )
                    )

            session.flush()
            memberships = self._group_members_by_user(session)
            payload = self._user_payload(user, groups=memberships.get(user.id, []))
            self._audit(
                action="update_user",
                outcome="ok",
                details={"user_id": user.id, "username": user.username},
            )
            return payload

    def delete_user(self, user_id: str) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user = (
                session.query(FileAdminUser).filter(FileAdminUser.id == user_id).one_or_none()
            )
            if user is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown user: {user_id}", status=404)

            removed_keys = 0
            for key in (
                session.query(FileAdminApiKey)
                .filter(FileAdminApiKey.user_id == user.id)
                .all()
            ):
                session.delete(key)
                removed_keys += 1

            for membership in (
                session.query(FileAdminGroupMember)
                .filter(FileAdminGroupMember.user_id == user.id)
                .all()
            ):
                session.delete(membership)

            payload = {"id": user.id, "username": user.username, "deleted": True}
            session.delete(user)
            self._audit(
                action="delete_user",
                outcome="ok",
                details={
                    "user_id": payload["id"],
                    "username": payload["username"],
                    "removed_api_keys": removed_keys,
                },
            )
            return payload

    def list_groups(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            members = self._group_members_by_group(session)
            groups = session.query(FileAdminGroup).order_by(FileAdminGroup.name.asc()).all()
            return [
                self._group_payload(group, members=members.get(group.id, []))
                for group in groups
            ]

    def get_group(self, group_id: str) -> dict[str, Any]:
        with self.session_manager.session() as session:
            group = (
                session.query(FileAdminGroup).filter(FileAdminGroup.id == group_id).one_or_none()
            )
            if group is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown group: {group_id}", status=404)
            members = self._group_members_by_group(session)
            return self._group_payload(group, members=members.get(group.id, []))

    def create_group(
        self,
        *,
        name: str,
        description: str = "",
        roles: Iterable[str] | None = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise AdminIdentityError("VALIDATION_ERROR", "group name is required")
        role_values = [str(role).strip() for role in (roles or []) if str(role).strip()]

        with self.session_manager.session() as session:
            exists = (
                session.query(FileAdminGroup)
                .filter(FileAdminGroup.name == clean_name)
                .one_or_none()
            )
            if exists is not None:
                raise AdminIdentityError(
                    "CONFLICT", f"group already exists: {clean_name}", status=409
                )

            group = FileAdminGroup(
                id=self._new_id("grp"),
                name=clean_name,
                description=description.strip(),
                roles_json=self._dump_json_list(role_values),
                is_active=bool(is_active),
            )
            session.add(group)
            session.flush()
            payload = self._group_payload(group, members=[])
            self._audit(
                action="create_group",
                outcome="ok",
                details={"group_id": group.id, "name": group.name},
            )
            return payload

    def update_group(self, group_id: str, *, data: dict[str, Any]) -> dict[str, Any]:
        with self.session_manager.session() as session:
            group = (
                session.query(FileAdminGroup).filter(FileAdminGroup.id == group_id).one_or_none()
            )
            if group is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown group: {group_id}", status=404)

            if "description" in data:
                group.description = str(data.get("description") or "").strip()
            if "roles" in data:
                roles = [
                    str(role).strip()
                    for role in (data.get("roles") or [])
                    if str(role).strip()
                ]
                group.roles_json = self._dump_json_list(roles)
            if "is_active" in data:
                group.is_active = bool(data.get("is_active"))

            session.flush()
            members = self._group_members_by_group(session)
            payload = self._group_payload(group, members=members.get(group.id, []))
            self._audit(
                action="update_group",
                outcome="ok",
                details={"group_id": group.id, "name": group.name},
            )
            return payload

    def delete_group(self, group_id: str) -> dict[str, Any]:
        with self.session_manager.session() as session:
            group = (
                session.query(FileAdminGroup).filter(FileAdminGroup.id == group_id).one_or_none()
            )
            if group is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown group: {group_id}", status=404)

            removed_members = 0
            for membership in (
                session.query(FileAdminGroupMember)
                .filter(FileAdminGroupMember.group_id == group.id)
                .all()
            ):
                session.delete(membership)
                removed_members += 1

            payload = {
                "id": group.id,
                "name": group.name,
                "deleted": True,
                "removed_members": removed_members,
            }
            session.delete(group)
            self._audit(
                action="delete_group",
                outcome="ok",
                details={"group_id": group.id, "name": group.name},
            )
            return payload

    def list_api_keys(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            query = session.query(FileAdminApiKey).order_by(FileAdminApiKey.created_at.desc())
            if not include_inactive:
                query = query.filter(FileAdminApiKey.is_active.is_(True))
            return [self._api_key_payload(record) for record in query.all()]

    def create_api_key(
        self,
        *,
        user_id: str,
        label: str,
        scopes: Iterable[str] | None = None,
        profile_name: str = "",
    ) -> dict[str, Any]:
        clean_profile = profile_name.strip()
        scope_values = [
            str(scope).strip()
            for scope in (scopes or [])
            if str(scope).strip()
        ]
        if clean_profile and f"profile:{clean_profile}" not in scope_values:
            scope_values.append(f"profile:{clean_profile}")
        if not scope_values:
            scope_values = ["profile:default"]

        with self.session_manager.session() as session:
            user = (
                session.query(FileAdminUser).filter(FileAdminUser.id == user_id).one_or_none()
            )
            if user is None:
                raise AdminIdentityError("NOT_FOUND", f"unknown user: {user_id}", status=404)

            secret = f"fka_{secrets.token_urlsafe(32)}"
            key_hash = hash_api_key(secret)
            record = FileAdminApiKey(
                id=self._new_id("key"),
                user_id=user.id,
                label=label.strip(),
                key_hash=key_hash,
                scopes_json=self._dump_json_list(scope_values),
                profile_name=clean_profile,
                is_active=True,
            )
            session.add(record)
            session.flush()
            payload = self._api_key_payload(record)
            payload["secret"] = secret
            self._audit(
                action="create_api_key",
                outcome="ok",
                details={"api_key_id": record.id, "user_id": record.user_id},
            )
            return payload

    def revoke_api_key(self, api_key_id: str) -> dict[str, Any]:
        with self.session_manager.session() as session:
            record = (
                session.query(FileAdminApiKey)
                .filter(FileAdminApiKey.id == api_key_id)
                .one_or_none()
            )
            if record is None:
                raise AdminIdentityError(
                    "NOT_FOUND", f"unknown api key: {api_key_id}", status=404
                )
            record.is_active = False
            record.revoked_at = datetime.now(timezone.utc)
            session.flush()
            payload = self._api_key_payload(record)
            self._audit(
                action="revoke_api_key",
                outcome="ok",
                details={"api_key_id": record.id, "user_id": record.user_id},
            )
            return payload

    def resolve_dynamic_api_key(
        self,
        *,
        token: str,
        profile_name: str,
    ) -> DynamicApiKeyPrincipal | None:
        candidate = str(token or "").strip()
        if not candidate:
            return None
        candidate_hash = hash_api_key(candidate)

        with self.session_manager.session() as session:
            record = (
                session.query(FileAdminApiKey)
                .filter(FileAdminApiKey.key_hash == candidate_hash)
                .filter(FileAdminApiKey.is_active.is_(True))
                .one_or_none()
            )
            if record is None:
                # Diagnostic: check total key count to distinguish
                # "empty table" from "hash mismatch".
                total_keys = session.query(FileAdminApiKey).count()
                active_keys = (
                    session.query(FileAdminApiKey)
                    .filter(FileAdminApiKey.is_active.is_(True))
                    .count()
                )
                if self.logger:
                    self.logger.warning(
                        "dynamic_key_lookup_miss",
                        profile=profile_name,
                        hash_prefix=candidate_hash[:12],
                        total_keys=total_keys,
                        active_keys=active_keys,
                    )
                return None
            if record.revoked_at is not None:
                return None
            if record.profile_name and record.profile_name != profile_name:
                if self.logger:
                    self.logger.warning(
                        "dynamic_key_profile_mismatch",
                        key_profile=record.profile_name,
                        request_profile=profile_name,
                    )
                return None

            user = (
                session.query(FileAdminUser)
                .filter(FileAdminUser.id == record.user_id)
                .one_or_none()
            )
            if user is None or not bool(user.is_active):
                if self.logger:
                    self.logger.warning(
                        "dynamic_key_user_invalid",
                        user_id=record.user_id,
                        user_found=user is not None,
                        user_active=bool(user.is_active) if user else False,
                    )
                return None

            permissions = set(self._parse_json_list(record.scopes_json))
            member_group_ids = [
                str(item.group_id)
                for item in session.query(FileAdminGroupMember)
                .filter(FileAdminGroupMember.user_id == user.id)
                .all()
            ]
            if member_group_ids:
                for group in (
                    session.query(FileAdminGroup)
                    .filter(FileAdminGroup.id.in_(member_group_ids))
                    .all()
                ):
                    permissions.update(self._parse_json_list(group.roles_json))

            role = "admin" if ("*" in permissions or "admin" in permissions) else "viewer"
            if not _allows_profile_permission(permissions, profile_name):
                if self.logger:
                    self.logger.warning(
                        "dynamic_key_permission_denied",
                        profile=profile_name,
                        permissions=sorted(permissions),
                    )
                return None
            if "admin" in permissions:
                permissions.add("*")

            return DynamicApiKeyPrincipal(
                api_key_id=record.id,
                user_id=user.id,
                username=user.username,
                role=role,
                permissions=tuple(sorted(permissions)),
                profile_name=profile_name,
            )
