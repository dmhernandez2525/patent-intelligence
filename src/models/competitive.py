"""Competitive intelligence and portfolio monitoring models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class MonitorStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class CompetitorMonitor(TimestampMixin, Base):
    """Tracks a competitor organization for patent activity."""

    __tablename__ = "competitor_monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    competitor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    cpc_focus: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    __table_args__ = (
        Index("ix_comp_monitors_user_status", "user_id", "status"),
    )


class PortfolioComparison(TimestampMixin, Base):
    """Snapshot of a portfolio comparison between two entities."""

    __tablename__ = "portfolio_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    entity_a: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_b: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    comparison_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    overlap_score: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class AcquisitionTarget(TimestampMixin, Base):
    """M&A target identified through patent portfolio analysis."""

    __tablename__ = "acquisition_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    target_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    patent_count: Mapped[int] = mapped_column(Integer, default=0)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    cpc_overlap: Mapped[list] = mapped_column(JSONB, default=list)
    analysis_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_acq_targets_user", "user_id"),
    )
