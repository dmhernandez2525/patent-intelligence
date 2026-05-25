"""Add core patent, watchlist, and ingestion tables.

Revision ID: 20260215_0001a
Revises: 20260215_0001
Create Date: 2026-02-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260215_0001a"
down_revision: str | None = "20260215_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "patents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patent_number", sa.String(length=50), nullable=False),
        sa.Column("application_number", sa.String(length=50), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("grant_date", sa.Date(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("priority_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("cpc_codes", postgresql.ARRAY(sa.String(length=20)), nullable=True),
        sa.Column("ipc_codes", postgresql.ARRAY(sa.String(length=20)), nullable=True),
        sa.Column("uspc_codes", postgresql.ARRAY(sa.String(length=20)), nullable=True),
        sa.Column("assignee", sa.Text(), nullable=True),
        sa.Column("assignee_organization", sa.Text(), nullable=True),
        sa.Column("inventors", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("inventor_countries", postgresql.ARRAY(sa.String(length=5)), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("patent_type", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=5), nullable=False, server_default="US"),
        sa.Column("kind_code", sa.String(length=5), nullable=True),
        sa.Column("patent_term_adjustment_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("patent_term_extension_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "terminal_disclaimer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cited_by_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="uspto"),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patent_number"),
    )
    op.create_index("ix_patents_patent_number", "patents", ["patent_number"], unique=False)
    op.create_index("ix_patents_application_number", "patents", ["application_number"])
    op.create_index("ix_patents_expiration_date", "patents", ["expiration_date"])
    op.create_index("ix_patents_assignee_organization", "patents", ["assignee_organization"])
    op.create_index("ix_patents_status", "patents", ["status"])
    op.create_index("ix_patents_country", "patents", ["country"])
    op.create_index(
        "ix_patents_cpc_gin",
        "patents",
        ["cpc_codes"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_patents_title_trgm",
        "patents",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index("ix_patents_filing_date", "patents", ["filing_date"])
    op.create_index("ix_patents_country_status", "patents", ["country", "status"])

    op.create_table(
        "patent_claims",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("claim_number", sa.Integer(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=20), nullable=False, server_default="independent"),
        sa.Column("parent_claim_number", sa.Integer(), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claims_patent_number",
        "patent_claims",
        ["patent_id", "claim_number"],
        unique=True,
    )

    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("citing_patent_id", sa.Integer(), nullable=False),
        sa.Column("cited_patent_id", sa.Integer(), nullable=True),
        sa.Column("cited_patent_number", sa.String(length=50), nullable=False),
        sa.Column("citation_type", sa.String(length=20), nullable=False, server_default="patent"),
        sa.Column("category", sa.String(length=5), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["citing_patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cited_patent_id"], ["patents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_citing_patent_id", "citations", ["citing_patent_id"])
    op.create_index("ix_citations_cited_patent_id", "citations", ["cited_patent_id"])

    op.create_table(
        "maintenance_fees",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("fee_year", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("amount_usd", sa.Float(), nullable=True),
        sa.Column("grace_period_end", sa.Date(), nullable=True),
        sa.Column("surcharge_amount", sa.Float(), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_fees_patent_id", "maintenance_fees", ["patent_id"])
    op.create_index(
        "ix_maintenance_patent_year",
        "maintenance_fees",
        ["patent_id", "fee_year"],
        unique=True,
    )
    op.create_index("ix_maintenance_due_date", "maintenance_fees", ["due_date"])
    op.create_index("ix_maintenance_status", "maintenance_fees", ["status"])

    op.create_table(
        "patent_families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("family_id", sa.String(length=50), nullable=False),
        sa.Column("family_type", sa.String(length=20), nullable=False, server_default="simple"),
        sa.Column("earliest_priority_date", sa.Date(), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id"),
    )
    op.create_index("ix_patent_families_family_id", "patent_families", ["family_id"])

    op.create_table(
        "patent_family_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.ForeignKeyConstraint(["family_id"], ["patent_families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patent_family_members_family_id", "patent_family_members", ["family_id"])
    op.create_index("ix_patent_family_members_patent_id", "patent_family_members", ["patent_id"])
    op.create_index(
        "ix_family_members_unique",
        "patent_family_members",
        ["family_id", "patent_id"],
        unique=True,
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_value", sa.String(length=255), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, server_default="default"),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("notify_expiration", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_maintenance", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_citations", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notify_new_patents", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expiration_lead_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("maintenance_lead_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_ts(),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watchlist_items_item_type", "watchlist_items", ["item_type"])
    op.create_index("ix_watchlist_items_item_value", "watchlist_items", ["item_value"])
    op.create_index("ix_watchlist_items_patent_id", "watchlist_items", ["patent_id"])
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_user_type", "watchlist_items", ["user_id", "item_type"])
    op.create_index(
        "ix_watchlist_user_value",
        "watchlist_items",
        ["user_id", "item_value"],
        unique=True,
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("watchlist_item_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_patent_number", sa.String(length=50), nullable=True),
        sa.Column("related_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trigger_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["watchlist_item_id"], ["watchlist_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_watchlist_item_id", "alerts", ["watchlist_item_id"])
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_trigger_date", "alerts", ["trigger_date"])
    op.create_index("ix_alerts_is_read", "alerts", ["is_read"])
    op.create_index("ix_alerts_unread", "alerts", ["watchlist_item_id", "is_read"])
    op.create_index("ix_alerts_trigger", "alerts", ["trigger_date"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("job_type", sa.String(length=20), nullable=False, server_default="full"),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_jobs_source", "ingestion_jobs", ["source"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "ingestion_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("last_sync_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_patent_date", sa.String(length=20), nullable=True),
        sa.Column("total_patents_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_checkpoints")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_source", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index("ix_alerts_trigger", table_name="alerts")
    op.drop_index("ix_alerts_unread", table_name="alerts")
    op.drop_index("ix_alerts_is_read", table_name="alerts")
    op.drop_index("ix_alerts_trigger_date", table_name="alerts")
    op.drop_index("ix_alerts_alert_type", table_name="alerts")
    op.drop_index("ix_alerts_watchlist_item_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_watchlist_user_value", table_name="watchlist_items")
    op.drop_index("ix_watchlist_user_type", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_patent_id", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_item_value", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_item_type", table_name="watchlist_items")
    op.drop_table("watchlist_items")

    op.drop_index("ix_family_members_unique", table_name="patent_family_members")
    op.drop_index("ix_patent_family_members_patent_id", table_name="patent_family_members")
    op.drop_index("ix_patent_family_members_family_id", table_name="patent_family_members")
    op.drop_table("patent_family_members")

    op.drop_index("ix_patent_families_family_id", table_name="patent_families")
    op.drop_table("patent_families")

    op.drop_index("ix_maintenance_status", table_name="maintenance_fees")
    op.drop_index("ix_maintenance_due_date", table_name="maintenance_fees")
    op.drop_index("ix_maintenance_patent_year", table_name="maintenance_fees")
    op.drop_index("ix_maintenance_fees_patent_id", table_name="maintenance_fees")
    op.drop_table("maintenance_fees")

    op.drop_index("ix_citations_cited_patent_id", table_name="citations")
    op.drop_index("ix_citations_citing_patent_id", table_name="citations")
    op.drop_table("citations")

    op.drop_index("ix_claims_patent_number", table_name="patent_claims")
    op.drop_table("patent_claims")

    op.drop_index("ix_patents_country_status", table_name="patents")
    op.drop_index("ix_patents_filing_date", table_name="patents")
    op.drop_index("ix_patents_title_trgm", table_name="patents")
    op.drop_index("ix_patents_cpc_gin", table_name="patents")
    op.drop_index("ix_patents_country", table_name="patents")
    op.drop_index("ix_patents_status", table_name="patents")
    op.drop_index("ix_patents_assignee_organization", table_name="patents")
    op.drop_index("ix_patents_expiration_date", table_name="patents")
    op.drop_index("ix_patents_application_number", table_name="patents")
    op.drop_index("ix_patents_patent_number", table_name="patents")
    op.drop_table("patents")
