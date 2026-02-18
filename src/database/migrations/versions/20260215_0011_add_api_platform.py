"""Add API platform: keys, webhooks, deliveries.

Revision ID: 20260215_0011
Revises: 20260215_0010
Create Date: 2026-02-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260215_0011"
down_revision = "20260215_0010"
branch_labels = None
depends_on = None


def _ts() -> sa.Column:
    return sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("tier", sa.String(20), server_default=sa.text("'free'")),
        sa.Column("scopes", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("rate_limit_per_minute", sa.Integer(), server_default=sa.text("100")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_key_user", "api_keys", ["user_id"])
    op.create_index("ix_api_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_key_active", "api_keys", ["is_active", "expires_at"])

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column("events", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_webhook_user", "webhook_endpoints", ["user_id"])
    op.create_index("ix_webhook_active", "webhook_endpoints", ["is_active"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("endpoint_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("1")),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(
            ["endpoint_id"], ["webhook_endpoints.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_delivery_endpoint", "webhook_deliveries", ["endpoint_id"])
    op.create_index("ix_delivery_success", "webhook_deliveries", ["success", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_delivery_success")
    op.drop_index("ix_delivery_endpoint")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_webhook_active")
    op.drop_index("ix_webhook_user")
    op.drop_table("webhook_endpoints")
    op.drop_index("ix_api_key_active")
    op.drop_index("ix_api_key_prefix")
    op.drop_index("ix_api_key_user")
    op.drop_table("api_keys")
