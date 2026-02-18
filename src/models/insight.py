"""AI-powered patent insight and analysis models."""

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


class InsightType(StrEnum):
    SUMMARY = "summary"
    CLAIM_ANALYSIS = "claim_analysis"
    PATENTABILITY = "patentability"
    FTO_ANALYSIS = "fto_analysis"
    NL_QUERY = "nl_query"
    COMPETITIVE_BRIEF = "competitive_brief"


class InsightStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PatentInsight(TimestampMixin, Base):
    """AI-generated insight or analysis for a patent or query."""

    __tablename__ = "patent_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    patent_id: Mapped[int | None] = mapped_column(
        ForeignKey("patents.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    insight_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InsightStatus.PENDING.value,
    )
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_patent_insights_user_type", "user_id", "insight_type"),
    )


class InsightTemplate(TimestampMixin, Base):
    """Reusable prompt template for generating patent insights."""

    __tablename__ = "insight_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    insight_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
