"""Add shared watchlist and research project models.

Revision ID: 20260215_0002
Revises: 20260215_0001a
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260215_0002"
down_revision: str | None = "20260215_0001a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "shared_watchlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shared_watchlists_owner_id", "shared_watchlists", ["owner_id"], unique=False)

    op.create_table(
        "shared_watchlist_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False, server_default="viewer"),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["watchlist_id"], ["shared_watchlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shared_watchlist_member_unique",
        "shared_watchlist_members",
        ["watchlist_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "ix_shared_watchlist_members_watchlist_id",
        "shared_watchlist_members",
        ["watchlist_id"],
        unique=False,
    )
    op.create_index(
        "ix_shared_watchlist_members_user_id",
        "shared_watchlist_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "shared_watchlist_invites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("invite_token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["watchlist_id"], ["shared_watchlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_index(
        "ix_shared_watchlist_invites_watchlist_id",
        "shared_watchlist_invites",
        ["watchlist_id"],
        unique=False,
    )
    op.create_index(
        "ix_shared_watchlist_invites_invited_email",
        "shared_watchlist_invites",
        ["invited_email"],
        unique=False,
    )
    op.create_index(
        "ix_shared_watchlist_invite_status",
        "shared_watchlist_invites",
        ["status", "expires_at"],
        unique=False,
    )

    op.create_table(
        "shared_watchlist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_value", sa.String(length=255), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=True),
        sa.Column("added_by_user_id", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["watchlist_id"], ["shared_watchlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shared_watchlist_item_unique",
        "shared_watchlist_items",
        ["watchlist_id", "item_type", "item_value"],
        unique=True,
    )
    op.create_index(
        "ix_shared_watchlist_items_watchlist_id",
        "shared_watchlist_items",
        ["watchlist_id"],
        unique=False,
    )

    op.create_table(
        "research_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_projects_name", "research_projects", ["name"], unique=False)
    op.create_index("ix_research_projects_status", "research_projects", ["status"], unique=False)
    op.create_index("ix_research_projects_owner_id", "research_projects", ["owner_id"], unique=False)

    op.create_table(
        "research_project_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False, server_default="viewer"),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_project_member_unique",
        "research_project_members",
        ["project_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "ix_research_project_members_project_id",
        "research_project_members",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "research_project_patents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=True),
        sa.Column("patent_number", sa.String(length=50), nullable=False),
        sa.Column("added_by_user_id", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_project_patent_unique",
        "research_project_patents",
        ["project_id", "patent_number"],
        unique=True,
    )
    op.create_index(
        "ix_research_project_patents_project_id",
        "research_project_patents",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_project_patents_project_id", table_name="research_project_patents")
    op.drop_index("ix_research_project_patent_unique", table_name="research_project_patents")
    op.drop_table("research_project_patents")

    op.drop_index("ix_research_project_members_project_id", table_name="research_project_members")
    op.drop_index("ix_research_project_member_unique", table_name="research_project_members")
    op.drop_table("research_project_members")

    op.drop_index("ix_research_projects_owner_id", table_name="research_projects")
    op.drop_index("ix_research_projects_status", table_name="research_projects")
    op.drop_index("ix_research_projects_name", table_name="research_projects")
    op.drop_table("research_projects")

    op.drop_index("ix_shared_watchlist_items_watchlist_id", table_name="shared_watchlist_items")
    op.drop_index("ix_shared_watchlist_item_unique", table_name="shared_watchlist_items")
    op.drop_table("shared_watchlist_items")

    op.drop_index("ix_shared_watchlist_invite_status", table_name="shared_watchlist_invites")
    op.drop_index("ix_shared_watchlist_invites_invited_email", table_name="shared_watchlist_invites")
    op.drop_index("ix_shared_watchlist_invites_watchlist_id", table_name="shared_watchlist_invites")
    op.drop_table("shared_watchlist_invites")

    op.drop_index("ix_shared_watchlist_members_user_id", table_name="shared_watchlist_members")
    op.drop_index("ix_shared_watchlist_members_watchlist_id", table_name="shared_watchlist_members")
    op.drop_index("ix_shared_watchlist_member_unique", table_name="shared_watchlist_members")
    op.drop_table("shared_watchlist_members")

    op.drop_index("ix_shared_watchlists_owner_id", table_name="shared_watchlists")
    op.drop_table("shared_watchlists")
