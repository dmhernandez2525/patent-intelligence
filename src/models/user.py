"""User, preferences, and user activity models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.organization import Organization, OrganizationInvite, OrganizationMember


class UserRole(StrEnum):
    """Application roles for RBAC."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(TimestampMixin, Base):
    """Platform user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.VIEWER.value, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    preferences: Mapped[UserPreference | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[list[UserActivityLog]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    organization_memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_organizations: Mapped[list[Organization]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Organization.owner_id",
    )
    sent_organization_invites: Mapped[list[OrganizationInvite]] = relationship(
        back_populates="invited_by",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationInvite.invited_by_user_id",
    )


class UserPreference(TimestampMixin, Base):
    """Per-user personalization preferences."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    default_search_mode: Mapped[str] = mapped_column(String(20), default="hybrid")
    alert_frequency: Mapped[str] = mapped_column(String(20), default="immediate")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="preferences")


class UserActivityLog(TimestampMixin, Base):
    """Auditable user actions."""

    __tablename__ = "user_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User | None] = relationship(back_populates="activity_logs")

    __table_args__ = (
        Index("ix_activity_user_event", "user_id", "event_type"),
        Index("ix_activity_created", "created_at"),
    )
