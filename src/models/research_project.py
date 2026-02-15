"""Research project collaboration models."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patent import Patent
    from src.models.user import User


class ProjectStatus(StrEnum):
    """Lifecycle state for research projects."""

    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectPermission(StrEnum):
    """Project member permissions."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class ResearchProject(TimestampMixin, Base):
    """Container for collaborative patent research."""

    __tablename__ = "research_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE.value, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    owner: Mapped[User] = relationship()
    members: Mapped[list[ResearchProjectMember]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    patents: Mapped[list[ResearchProjectPatent]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ResearchProjectMember(TimestampMixin, Base):
    """Project membership with role-specific permissions."""

    __tablename__ = "research_project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    permission: Mapped[str] = mapped_column(String(20), default=ProjectPermission.VIEWER.value)

    project: Mapped[ResearchProject] = relationship(back_populates="members")
    user: Mapped[User] = relationship()

    __table_args__ = (Index("ix_research_project_member_unique", "project_id", "user_id", unique=True),)


class ResearchProjectPatent(TimestampMixin, Base):
    """Patent assignment within a project scope."""

    __tablename__ = "research_project_patents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        index=True,
    )
    patent_id: Mapped[int | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patent_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    added_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    project: Mapped[ResearchProject] = relationship(back_populates="patents")
    patent: Mapped[Patent | None] = relationship()
    added_by: Mapped[User] = relationship()

    __table_args__ = (
        Index("ix_research_project_patent_unique", "project_id", "patent_number", unique=True),
    )
