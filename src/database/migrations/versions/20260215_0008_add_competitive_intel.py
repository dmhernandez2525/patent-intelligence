"""Add competitive intelligence models.

Revision ID: 20260215_0008
Revises: 20260215_0007
Create Date: 2026-02-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260215_0008"
down_revision = "20260215_0007"
branch_labels = None
depends_on = None


def _ts():
    return sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "competitor_monitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("cpc_focus", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comp_monitors_user_status", "competitor_monitors", ["user_id", "status"])

    op.create_table(
        "portfolio_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entity_a", sa.String(200), nullable=False),
        sa.Column("entity_b", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("comparison_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("overlap_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_portfolio_comp_user", "portfolio_comparisons", ["user_id"])

    op.create_table(
        "acquisition_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_name", sa.String(200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("patent_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("cpc_overlap", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("analysis_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_starred", sa.Boolean(), server_default=sa.text("false")),
        _ts(), _ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_acq_targets_user", "acquisition_targets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_acq_targets_user")
    op.drop_table("acquisition_targets")
    op.drop_index("ix_portfolio_comp_user")
    op.drop_table("portfolio_comparisons")
    op.drop_index("ix_comp_monitors_user_status")
    op.drop_table("competitor_monitors")
