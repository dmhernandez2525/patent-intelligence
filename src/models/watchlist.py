"""Watchlist and Alert models for tracking patents and notifications."""

from datetime import datetime
from enum import Enum

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class WatchItemType(str, Enum):
    """Types of items that can be watched."""

    PATENT = "patent"
    CPC_CODE = "cpc_code"
    ASSIGNEE = "assignee"
    INVENTOR = "inventor"


class AlertType(str, Enum):
    """Types of alerts."""

    EXPIRATION = "expiration"
    MAINTENANCE_FEE = "maintenance_fee"
    NEW_CITATION = "new_citation"
    STATUS_CHANGE = "status_change"
    NEW_PATENT = "new_patent"


class AlertPriority(str, Enum):
    """Alert priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WatchlistItem(TimestampMixin, Base):
    """An item being watched by a user."""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # What's being watched
    item_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    item_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Optional link to patent
    patent_id: Mapped[int | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL"), index=True
    )

    # User identification (simple string for now, can be extended)
    user_id: Mapped[str] = mapped_column(String(50), default="default", index=True)

    # Watch settings
    name: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    notify_expiration: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_maintenance: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_citations: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_new_patents: Mapped[bool] = mapped_column(Boolean, default=False)

    # Expiration alert lead time (days before)
    expiration_lead_days: Mapped[int] = mapped_column(Integer, default=90)
    maintenance_lead_days: Mapped[int] = mapped_column(Integer, default=30)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="watchlist_item", cascade="all, delete"
    )

    __table_args__ = (
        Index("ix_watchlist_user_type", "user_id", "item_type"),
        Index("ix_watchlist_user_value", "user_id", "item_value", unique=True),
    )


class Alert(TimestampMixin, Base):
    """An alert notification for a watched item."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    watchlist_item_id: Mapped[int] = mapped_column(
        ForeignKey("watchlist_items.id", ondelete="CASCADE"), index=True
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Related entity
    related_patent_number: Mapped[str | None] = mapped_column(String(50))
    related_data: Mapped[dict | None] = mapped_column(JSONB)

    # Alert timing
    trigger_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Status tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    watchlist_item: Mapped["WatchlistItem"] = relationship(back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_unread", "watchlist_item_id", "is_read"),
        Index("ix_alerts_trigger", "trigger_date"),
    )
