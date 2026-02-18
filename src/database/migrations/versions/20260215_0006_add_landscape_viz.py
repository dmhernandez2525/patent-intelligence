"""Add landscape visualization snapshots and points.

Revision ID: 20260215_0006
Revises: 20260215_0005
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260215_0006"
down_revision: str | None = "20260215_0005"
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
        "landscape_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reduction_method", sa.String(20), nullable=False,
                   server_default=sa.text("'umap'")),
        sa.Column("cluster_method", sa.String(20), nullable=False,
                   server_default=sa.text("'kmeans'")),
        sa.Column("num_clusters", sa.Integer(), nullable=False,
                   server_default=sa.text("5")),
        sa.Column("patent_count", sa.Integer(), nullable=False,
                   server_default=sa.text("0")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False,
                   server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landscape_snapshots_user_id",
                     "landscape_snapshots", ["user_id"])
    op.create_index("ix_landscape_snapshots_user_status",
                     "landscape_snapshots", ["user_id", "status"])

    op.create_table(
        "landscape_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("cluster_label", sa.String(100), nullable=True),
        sa.Column("point_metadata", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["landscape_snapshots.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patent_id"], ["patents.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_landscape_points_snapshot_id",
                     "landscape_points", ["snapshot_id"])
    op.create_index("ix_landscape_points_snapshot_cluster",
                     "landscape_points", ["snapshot_id", "cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_landscape_points_snapshot_cluster", "landscape_points")
    op.drop_index("ix_landscape_points_snapshot_id", "landscape_points")
    op.drop_table("landscape_points")

    op.drop_index("ix_landscape_snapshots_user_status", "landscape_snapshots")
    op.drop_index("ix_landscape_snapshots_user_id", "landscape_snapshots")
    op.drop_table("landscape_snapshots")
