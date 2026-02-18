"""Custom analytics engine models for saved queries and metrics."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class MetricType(StrEnum):
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    TREND = "trend"
    DISTRIBUTION = "distribution"


class QueryStatus(StrEnum):
    DRAFT = "draft"
    SAVED = "saved"
    ARCHIVED = "archived"


class SavedQuery(TimestampMixin, Base):
    """A user-defined patent analytics query."""

    __tablename__ = "saved_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    query_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="saved")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_saved_queries_user_status", "user_id", "status"),
    )


class CustomMetric(TimestampMixin, Base):
    """A user-defined metric computed from patent data."""

    __tablename__ = "custom_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_value: Mapped[dict | None] = mapped_column(JSONB)
    last_computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class AnalyticsSchedule(TimestampMixin, Base):
    """Schedule for recurring analytics execution."""

    __tablename__ = "analytics_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    query_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_queries.id", ondelete="SET NULL"),
    )
    metric_id: Mapped[int | None] = mapped_column(
        ForeignKey("custom_metrics.id", ondelete="SET NULL"),
    )
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    __table_args__ = (
        Index("ix_analytics_sched_active", "is_active", "next_run_at"),
    )
