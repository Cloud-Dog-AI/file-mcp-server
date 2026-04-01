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

"""
file-mcp-server — file_mcp_server/db/models.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Database runtime module for models.py.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cloud_dog_db import PlatformBase, TimestampMixin


class FilePlatformDbState(PlatformBase, TimestampMixin):
    """Minimal service-owned table proving schema ownership and migrations."""

    __tablename__ = "file_platform_db_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")


class FileAdminUser(PlatformBase, TimestampMixin):
    """Admin user record used by config CRUD identity surfaces."""

    __tablename__ = "file_admin_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FileAdminGroup(PlatformBase, TimestampMixin):
    """Admin group record with role assignments encoded as JSON text."""

    __tablename__ = "file_admin_groups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    roles_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FileAdminGroupMember(PlatformBase, TimestampMixin):
    """Join table mapping users into groups."""

    __tablename__ = "file_admin_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_file_admin_group_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("file_admin_groups.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("file_admin_users.id"), nullable=False
    )


class FileStorageProfile(PlatformBase, TimestampMixin):
    """Storage profile — single source of truth for profile configuration.

    Replaces both the YAML config.yaml and the flat storage-profiles.json.
    Each row holds the full ProfileConfig as serialised JSON in config_json.
    """

    __tablename__ = "file_storage_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FileAdminApiKey(PlatformBase, TimestampMixin):
    """API-key records used for dynamic auth and admin key management."""

    __tablename__ = "file_admin_api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("file_admin_users.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    scopes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
