"""Alert notification channel and delivery tracking models."""

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class ChannelType(StrEnum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class DigestFrequency(StrEnum):
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationChannel(TimestampMixin, Base):
    """A configured notification delivery channel for a user."""
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deliveries: Mapped[list[AlertDelivery]] = relationship(
        back_populates="channel", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_notif_channels_user_active", "user_id", "is_active"),
    )


class AlertSchedule(TimestampMixin, Base):
    """User's alert delivery schedule preferences."""
    __tablename__ = "alert_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"),
    )
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="immediate",
    )
    delivery_hour: Mapped[int] = mapped_column(Integer, default=9)
    delivery_day: Mapped[int] = mapped_column(Integer, default=1)
    alert_types: Mapped[list] = mapped_column(JSONB, default=list)
    min_priority: Mapped[str] = mapped_column(String(20), default="low")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AlertDelivery(TimestampMixin, Base):
    """Tracks delivery of alerts through channels."""
    __tablename__ = "alert_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), index=True,
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    channel: Mapped[NotificationChannel] = relationship(
        back_populates="deliveries",
    )

    __table_args__ = (
        Index("ix_alert_deliveries_pending", "status", "next_retry_at"),
    )


class AlertTemplate(TimestampMixin, Base):
    """Custom alert email/message templates."""
    __tablename__ = "alert_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True,
    )
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_template: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
