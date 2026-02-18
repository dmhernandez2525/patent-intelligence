"""Add research reports, templates, and schedules.

Revision ID: 20260215_0005
Revises: 20260215_0004
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260215_0005"
down_revision: str | None = "20260215_0004"
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
    # report_templates has no FK dependencies, create first
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_config", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False,
                   server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean(), nullable=False,
                   server_default=sa.text("true")),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "research_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False,
                   server_default=sa.text("'custom'")),
        sa.Column("output_format", sa.String(10), nullable=False,
                   server_default=sa.text("'pdf'")),
        sa.Column("status", sa.String(20), nullable=False,
                   server_default=sa.text("'pending'")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["research_projects.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_reports_user_id",
                     "research_reports", ["user_id"])
    op.create_index("ix_research_reports_project_id",
                     "research_reports", ["project_id"])
    op.create_index("ix_research_reports_user_status",
                     "research_reports", ["user_id", "status"])

    op.create_table(
        "report_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("output_format", sa.String(10), nullable=False,
                   server_default=sa.text("'pdf'")),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("frequency", sa.String(20), nullable=False,
                   server_default=sa.text("'weekly'")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                   server_default=sa.text("true")),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["research_projects.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_schedules_user_id",
                     "report_schedules", ["user_id"])
    op.create_index("ix_report_schedules_active_next",
                     "report_schedules", ["is_active", "next_run_at"])


def downgrade() -> None:
    op.drop_index("ix_report_schedules_active_next", "report_schedules")
    op.drop_index("ix_report_schedules_user_id", "report_schedules")
    op.drop_table("report_schedules")

    op.drop_index("ix_research_reports_user_status", "research_reports")
    op.drop_index("ix_research_reports_project_id", "research_reports")
    op.drop_index("ix_research_reports_user_id", "research_reports")
    op.drop_table("research_reports")

    op.drop_table("report_templates")
