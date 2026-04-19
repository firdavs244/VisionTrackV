"""Initial schema: users, cameras, parts, activity_logs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("admin", "operator", name="user_role")
camera_status = sa.Enum("active", "inactive", "error", name="camera_status")
part_status = sa.Enum("verified", "review", "rejected", name="part_status")
activity_type = sa.Enum("ok", "info", "warn", "error", name="activity_type")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_created_at", "users", ["created_at"])

    op.create_table(
        "cameras",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=False, server_default=""),
        sa.Column("status", camera_status, nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cameras_created_at", "cameras", ["created_at"])

    op.create_table(
        "parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("serial_number", sa.String(32), nullable=False),
        sa.Column(
            "camera_id",
            sa.String(20),
            sa.ForeignKey("cameras.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", part_status, nullable=False, server_default="review"),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("analysis_text", sa.Text(), nullable=True),
        sa.Column("ocr_backend", sa.String(20), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "scanned_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parts_serial_number", "parts", ["serial_number"])
    op.create_index("ix_parts_camera_created", "parts", ["camera_id", "created_at"])
    op.create_index("ix_parts_status", "parts", ["status"])
    op.create_index("ix_parts_is_deleted", "parts", ["is_deleted"])
    op.create_index("ix_parts_created_at", "parts", ["created_at"])

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", activity_type, nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.String(100), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index("ix_parts_created_at", table_name="parts")
    op.drop_index("ix_parts_is_deleted", table_name="parts")
    op.drop_index("ix_parts_status", table_name="parts")
    op.drop_index("ix_parts_camera_created", table_name="parts")
    op.drop_index("ix_parts_serial_number", table_name="parts")
    op.drop_table("parts")
    op.drop_index("ix_cameras_created_at", table_name="cameras")
    op.drop_table("cameras")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    activity_type.drop(bind, checkfirst=True)
    part_status.drop(bind, checkfirst=True)
    camera_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
