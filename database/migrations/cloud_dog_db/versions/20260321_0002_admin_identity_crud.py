"""file-mcp-server admin identity CRUD tables

Revision ID: 20260321_0002
Revises: 20260305_0001
Create Date: 2026-03-21 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260321_0002"
down_revision = "20260305_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_admin_users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(
        op.f("ix_file_admin_users_created_at"),
        "file_admin_users",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "file_admin_groups",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False),
        sa.Column("roles_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_file_admin_groups_created_at"),
        "file_admin_groups",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "file_admin_group_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["file_admin_groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["file_admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_file_admin_group_member"),
    )
    op.create_index(
        op.f("ix_file_admin_group_members_created_at"),
        "file_admin_group_members",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "file_admin_api_keys",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("key_hash", sa.String(length=256), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("profile_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["file_admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(
        op.f("ix_file_admin_api_keys_created_at"),
        "file_admin_api_keys",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_file_admin_api_keys_created_at"), table_name="file_admin_api_keys")
    op.drop_table("file_admin_api_keys")

    op.drop_index(
        op.f("ix_file_admin_group_members_created_at"),
        table_name="file_admin_group_members",
    )
    op.drop_table("file_admin_group_members")

    op.drop_index(op.f("ix_file_admin_groups_created_at"), table_name="file_admin_groups")
    op.drop_table("file_admin_groups")

    op.drop_index(op.f("ix_file_admin_users_created_at"), table_name="file_admin_users")
    op.drop_table("file_admin_users")
