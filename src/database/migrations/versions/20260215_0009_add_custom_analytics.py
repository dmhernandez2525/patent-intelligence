"""Add custom analytics engine models.

Revision ID: 20260215_0009
Revises: 20260215_0008
Create Date: 2026-02-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260215_0009"
down_revision = "20260215_0008"
branch_labels = None
depends_on = None


def _ts() -> sa.Column:
    return sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "saved_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query_config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("filters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), server_default=sa.text("'saved'")),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), server_default=sa.text("0")),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_saved_queries_user_status", "saved_queries", ["user_id", "status"])

    op.create_table(
        "custom_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("metric_type", sa.String(20), nullable=False),
        sa.Column("definition", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("current_value", postgresql.JSONB(), nullable=True),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_custom_metrics_user", "custom_metrics", ["user_id"])

    op.create_table(
        "analytics_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=True),
        sa.Column("metric_id", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.String(20), server_default=sa.text("'daily'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_id"], ["saved_queries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["metric_id"], ["custom_metrics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_analytics_sched_active", "analytics_schedules", ["is_active", "next_run_at"])


def downgrade() -> None:
    op.drop_index("ix_analytics_sched_active")
    op.drop_table("analytics_schedules")
    op.drop_index("ix_custom_metrics_user")
    op.drop_table("custom_metrics")
    op.drop_index("ix_saved_queries_user_status")
    op.drop_table("saved_queries")
