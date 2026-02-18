"""Add AI-powered patent insights and templates.

Revision ID: 20260215_0007
Revises: 20260215_0006
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260215_0007"
down_revision: str | None = "20260215_0006"
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
        "patent_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=True),
        sa.Column("insight_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                   server_default=sa.text("'pending'")),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patent_insights_user_id",
                     "patent_insights", ["user_id"])
    op.create_index("ix_patent_insights_patent_id",
                     "patent_insights", ["patent_id"])
    op.create_index("ix_patent_insights_user_type",
                     "patent_insights", ["user_id", "insight_type"])

    op.create_table(
        "insight_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("insight_type", sa.String(30), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False,
                   server_default=sa.text("false")),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_insight_templates_name"),
    )


def downgrade() -> None:
    op.drop_table("insight_templates")

    op.drop_index("ix_patent_insights_user_type", "patent_insights")
    op.drop_index("ix_patent_insights_patent_id", "patent_insights")
    op.drop_index("ix_patent_insights_user_id", "patent_insights")
    op.drop_table("patent_insights")
