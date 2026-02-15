"""Research report generation and template models."""

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


class ReportType(StrEnum):
    LANDSCAPE = "landscape"
    COMPETITIVE = "competitive"
    EXPIRATION = "expiration"
    PATENT_ANALYSIS = "patent_analysis"
    CUSTOM = "custom"


class ReportFormat(StrEnum):
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    JSON = "json"


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchReport(TimestampMixin, Base):
    """A generated research report tied to a user and optional project."""

    __tablename__ = "research_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ReportType.CUSTOM.value,
    )
    output_format: Mapped[str] = mapped_column(
        String(10), nullable=False, default=ReportFormat.PDF.value,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReportStatus.PENDING.value,
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_research_reports_user_status", "user_id", "status"),
    )


class ReportTemplate(TimestampMixin, Base):
    """Reusable template defining report layout and sections."""

    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class ReportSchedule(TimestampMixin, Base):
    """Recurring schedule for automatic report generation."""

    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    output_format: Mapped[str] = mapped_column(
        String(10), nullable=False, default=ReportFormat.PDF.value,
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="weekly",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_report_schedules_active_next", "is_active", "next_run_at"),
    )
