"""
file-mcp-server — file_mcp_server/db/models.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Database runtime module for models.py.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cloud_dog_db import PlatformBase, TimestampMixin


class FilePlatformDbState(PlatformBase, TimestampMixin):
    """Minimal service-owned table proving schema ownership and migrations."""

    __tablename__ = "file_platform_db_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
