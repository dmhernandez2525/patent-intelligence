"""Add notification channels, schedules, deliveries, and templates.

Revision ID: 20260215_0004
Revises: 20260215_0003
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260215_0004"
down_revision: str | None = "20260215_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                   server_default=sa.text("true")),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_channels_user_id",
                     "notification_channels", ["user_id"])
    op.create_index("ix_notif_channels_user_active",
                     "notification_channels", ["user_id", "is_active"])

    op.create_table(
        "alert_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False,
                   server_default=sa.text("'immediate'")),
        sa.Column("delivery_hour", sa.Integer(), nullable=False,
                   server_default=sa.text("9")),
        sa.Column("delivery_day", sa.Integer(), nullable=False,
                   server_default=sa.text("1")),
        sa.Column("alert_types", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("min_priority", sa.String(20), nullable=False,
                   server_default=sa.text("'low'")),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                   server_default=sa.text("true")),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["notification_channels.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_schedules_user_id",
                     "alert_schedules", ["user_id"])

    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                   server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False,
                   server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False,
                   server_default=sa.text("3")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["alert_id"], ["alerts.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["notification_channels.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_deliveries_alert_id",
                     "alert_deliveries", ["alert_id"])
    op.create_index("ix_alert_deliveries_pending",
                     "alert_deliveries", ["status", "next_retry_at"])

    op.create_table(
        "alert_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False,
                   server_default=sa.text("false")),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("alert_templates")

    op.drop_index("ix_alert_deliveries_pending", "alert_deliveries")
    op.drop_index("ix_alert_deliveries_alert_id", "alert_deliveries")
    op.drop_table("alert_deliveries")

    op.drop_index("ix_alert_schedules_user_id", "alert_schedules")
    op.drop_table("alert_schedules")

    op.drop_index("ix_notif_channels_user_active", "notification_channels")
    op.drop_index("ix_notification_channels_user_id", "notification_channels")
    op.drop_table("notification_channels")
