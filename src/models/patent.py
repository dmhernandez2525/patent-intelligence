from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import settings
from src.models.base import Base, TimestampMixin


class Patent(TimestampMixin, Base):
    __tablename__ = "patents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    application_number: Mapped[str | None] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # Dates
    filing_date: Mapped[date | None] = mapped_column(Date)
    grant_date: Mapped[date | None] = mapped_column(Date)
    publication_date: Mapped[date | None] = mapped_column(Date)
    priority_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Classification
    cpc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(20)))
    ipc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(20)))
    uspc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(20)))

    # Parties
    assignee: Mapped[str | None] = mapped_column(Text)
    assignee_organization: Mapped[str | None] = mapped_column(Text, index=True)
    inventors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    inventor_countries: Mapped[list[str] | None] = mapped_column(ARRAY(String(5)))

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    patent_type: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(5), default="US", index=True)
    kind_code: Mapped[str | None] = mapped_column(String(5))

    # Term adjustments
    patent_term_adjustment_days: Mapped[int] = mapped_column(Integer, default=0)
    patent_term_extension_days: Mapped[int] = mapped_column(Integer, default=0)
    terminal_disclaimer: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    cited_by_count: Mapped[int] = mapped_column(Integer, default=0)
    claim_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), default="uspto")
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Vector embedding
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimension), nullable=True
    )

    # Relationships
    claims: Mapped[list["PatentClaim"]] = relationship(back_populates="patent", cascade="all, delete")
    citations_made: Mapped[list["Citation"]] = relationship(
        back_populates="citing_patent",
        foreign_keys="Citation.citing_patent_id",
        cascade="all, delete",
    )
    cited_by: Mapped[list["Citation"]] = relationship(
        back_populates="cited_patent",
        foreign_keys="Citation.cited_patent_id",
        cascade="all, delete",
    )
    maintenance_fees: Mapped[list["MaintenanceFee"]] = relationship(
        back_populates="patent", cascade="all, delete"
    )
    family_memberships: Mapped[list["PatentFamilyMember"]] = relationship(
        back_populates="patent", cascade="all, delete"
    )

    __table_args__ = (
        Index("ix_patents_cpc_gin", "cpc_codes", postgresql_using="gin"),
        Index("ix_patents_title_trgm", "title", postgresql_using="gin",
              postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_patents_filing_date", "filing_date"),
        Index("ix_patents_country_status", "country", "status"),
    )


class PatentClaim(TimestampMixin, Base):
    __tablename__ = "patent_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"))
    claim_number: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(20), default="independent")
    parent_claim_number: Mapped[int | None] = mapped_column(Integer)

    patent: Mapped["Patent"] = relationship(back_populates="claims")

    __table_args__ = (
        Index("ix_claims_patent_number", "patent_id", "claim_number", unique=True),
    )


class Citation(TimestampMixin, Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    citing_patent_id: Mapped[int] = mapped_column(
        ForeignKey("patents.id", ondelete="CASCADE"), index=True
    )
    cited_patent_id: Mapped[int | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL"), index=True
    )
    cited_patent_number: Mapped[str] = mapped_column(String(50), nullable=False)
    citation_type: Mapped[str] = mapped_column(String(20), default="patent")
    category: Mapped[str | None] = mapped_column(String(5))

    citing_patent: Mapped["Patent"] = relationship(
        back_populates="citations_made", foreign_keys=[citing_patent_id]
    )
    cited_patent: Mapped["Patent | None"] = relationship(
        back_populates="cited_by", foreign_keys=[cited_patent_id]
    )


class MaintenanceFee(TimestampMixin, Base):
    __tablename__ = "maintenance_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"), index=True)
    fee_year: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    amount_usd: Mapped[float | None] = mapped_column(Float)
    grace_period_end: Mapped[date | None] = mapped_column(Date)
    surcharge_amount: Mapped[float | None] = mapped_column(Float)

    patent: Mapped["Patent"] = relationship(back_populates="maintenance_fees")

    __table_args__ = (
        Index("ix_maintenance_patent_year", "patent_id", "fee_year", unique=True),
        Index("ix_maintenance_due_date", "due_date"),
        Index("ix_maintenance_status", "status"),
    )


class PatentFamily(TimestampMixin, Base):
    __tablename__ = "patent_families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    family_type: Mapped[str] = mapped_column(String(20), default="simple")
    earliest_priority_date: Mapped[date | None] = mapped_column(Date)
    member_count: Mapped[int] = mapped_column(Integer, default=0)

    members: Mapped[list["PatentFamilyMember"]] = relationship(
        back_populates="family", cascade="all, delete"
    )


class PatentFamilyMember(Base):
    __tablename__ = "patent_family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("patent_families.id", ondelete="CASCADE"), index=True
    )
    patent_id: Mapped[int] = mapped_column(
        ForeignKey("patents.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member")

    family: Mapped["PatentFamily"] = relationship(back_populates="members")
    patent: Mapped["Patent"] = relationship(back_populates="family_memberships")

    __table_args__ = (
        Index("ix_family_members_unique", "family_id", "patent_id", unique=True),
    )
