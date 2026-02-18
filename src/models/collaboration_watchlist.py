"""Shared watchlist collaboration models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class SharedPermission(StrEnum):
    """Permissions available for collaboration entities."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class SharedWatchlist(TimestampMixin, Base):
    """A watchlist shared with collaborators."""

    __tablename__ = "shared_watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    owner: Mapped[User] = relationship()
    members: Mapped[list[SharedWatchlistMember]] = relationship(
        back_populates="watchlist",
        cascade="all, delete-orphan",
    )
    invites: Mapped[list[SharedWatchlistInvite]] = relationship(
        back_populates="watchlist",
        cascade="all, delete-orphan",
    )
    items: Mapped[list[SharedWatchlistItem]] = relationship(
        back_populates="watchlist",
        cascade="all, delete-orphan",
    )


class SharedWatchlistMember(TimestampMixin, Base):
    """Membership for shared watchlists."""

    __tablename__ = "shared_watchlist_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("shared_watchlists.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    permission: Mapped[str] = mapped_column(String(20), default=SharedPermission.VIEWER.value)

    watchlist: Mapped[SharedWatchlist] = relationship(back_populates="members")
    user: Mapped[User] = relationship()

    __table_args__ = (Index("ix_shared_watchlist_member_unique", "watchlist_id", "user_id", unique=True),)


class SharedWatchlistInvite(TimestampMixin, Base):
    """Invitation record for shared watchlists."""

    __tablename__ = "shared_watchlist_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("shared_watchlists.id", ondelete="CASCADE"),
        index=True,
    )
    invited_email: Mapped[str] = mapped_column(String(255), index=True)
    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    permission: Mapped[str] = mapped_column(String(20), default=SharedPermission.VIEWER.value)
    invite_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    watchlist: Mapped[SharedWatchlist] = relationship(back_populates="invites")
    invited_by: Mapped[User] = relationship()

    __table_args__ = (Index("ix_shared_watchlist_invite_status", "status", "expires_at"),)


class SharedWatchlistItem(TimestampMixin, Base):
    """Items tracked in a shared watchlist."""

    __tablename__ = "shared_watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("shared_watchlists.id", ondelete="CASCADE"),
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    item_value: Mapped[str] = mapped_column(String(255), index=True)
    patent_id: Mapped[int | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    added_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    watchlist: Mapped[SharedWatchlist] = relationship(back_populates="items")
    added_by: Mapped[User] = relationship()

    __table_args__ = (
        Index(
            "ix_shared_watchlist_item_unique",
            "watchlist_id",
            "item_type",
            "item_value",
            unique=True,
        ),
    )
