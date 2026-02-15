"""Add annotations, comments, and mention notifications.

Revision ID: 20260215_0003
Revises: 20260215_0002
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260215_0003"
down_revision: str | None = "20260215_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "collaborative_annotations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_annotation_patent_user",
        "collaborative_annotations",
        ["patent_id", "user_id"],
        unique=False,
    )

    op.create_table(
        "patent_comment_threads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patent_comment_threads_patent_id", "patent_comment_threads", ["patent_id"], unique=False)
    op.create_index("ix_patent_comment_threads_project_id", "patent_comment_threads", ["project_id"], unique=False)

    op.create_table(
        "patent_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["thread_id"], ["patent_comment_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["patent_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patent_comments_thread_id", "patent_comments", ["thread_id"], unique=False)
    op.create_index("ix_patent_comments_user_id", "patent_comments", ["user_id"], unique=False)
    op.create_index("ix_patent_comments_is_deleted", "patent_comments", ["is_deleted"], unique=False)
    op.create_index("ix_comment_thread_parent", "patent_comments", ["thread_id", "parent_comment_id"], unique=False)

    op.create_table(
        "mention_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["patent_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mention_notifications_user_id", "mention_notifications", ["user_id"], unique=False)
    op.create_index("ix_mention_notifications_is_read", "mention_notifications", ["is_read"], unique=False)
    op.create_index("ix_mention_user_unread", "mention_notifications", ["user_id", "is_read"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mention_user_unread", table_name="mention_notifications")
    op.drop_index("ix_mention_notifications_is_read", table_name="mention_notifications")
    op.drop_index("ix_mention_notifications_user_id", table_name="mention_notifications")
    op.drop_table("mention_notifications")

    op.drop_index("ix_comment_thread_parent", table_name="patent_comments")
    op.drop_index("ix_patent_comments_is_deleted", table_name="patent_comments")
    op.drop_index("ix_patent_comments_user_id", table_name="patent_comments")
    op.drop_index("ix_patent_comments_thread_id", table_name="patent_comments")
    op.drop_table("patent_comments")

    op.drop_index("ix_patent_comment_threads_project_id", table_name="patent_comment_threads")
    op.drop_index("ix_patent_comment_threads_patent_id", table_name="patent_comment_threads")
    op.drop_table("patent_comment_threads")

    op.drop_index("ix_annotation_patent_user", table_name="collaborative_annotations")
    op.drop_table("collaborative_annotations")
