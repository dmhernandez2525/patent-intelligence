"""Annotations, comment threads, and mention notifications."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class CollaborativeAnnotation(TimestampMixin, Base):
    """Annotation attached to a patent by a specific user."""

    __tablename__ = "collaborative_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship()

    __table_args__ = (Index("ix_annotation_patent_user", "patent_id", "user_id"),)


class PatentCommentThread(TimestampMixin, Base):
    """Top-level comment thread for a patent."""

    __tablename__ = "patent_comment_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    comments: Mapped[list[PatentComment]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )
    created_by: Mapped[User] = relationship()


class PatentComment(TimestampMixin, Base):
    """Threaded comment entry."""

    __tablename__ = "patent_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("patent_comment_threads.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("patent_comments.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped[PatentCommentThread] = relationship(back_populates="comments")
    parent_comment: Mapped[PatentComment | None] = relationship(
        remote_side="PatentComment.id",
        uselist=False,
    )
    user: Mapped[User] = relationship()
    mentions: Mapped[list[MentionNotification]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_comment_thread_parent", "thread_id", "parent_comment_id"),)


class MentionNotification(TimestampMixin, Base):
    """Notification generated from @mentions in comments."""

    __tablename__ = "mention_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("patent_comments.id", ondelete="CASCADE"),
        index=True,
    )
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()
    comment: Mapped[PatentComment] = relationship(back_populates="mentions")

    __table_args__ = (Index("ix_mention_user_unread", "user_id", "is_read"),)
