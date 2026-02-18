"""Patent landscape visualization and clustering models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ReductionMethod(StrEnum):
    TSNE = "tsne"
    UMAP = "umap"
    PCA = "pca"


class ClusterMethod(StrEnum):
    KMEANS = "kmeans"
    HDBSCAN = "hdbscan"
    DBSCAN = "dbscan"


class LandscapeSnapshot(TimestampMixin, Base):
    """Precomputed snapshot of a patent landscape visualization."""

    __tablename__ = "landscape_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reduction_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReductionMethod.UMAP.value,
    )
    cluster_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ClusterMethod.KMEANS.value,
    )
    num_clusters: Mapped[int] = mapped_column(Integer, default=5)
    patent_count: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_landscape_snapshots_user_status", "user_id", "status"),
    )


class LandscapePoint(Base):
    """Single patent point in a landscape visualization."""

    __tablename__ = "landscape_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("landscape_snapshots.id", ondelete="CASCADE"), index=True,
    )
    patent_id: Mapped[int] = mapped_column(
        ForeignKey("patents.id", ondelete="CASCADE"),
    )
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cluster_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    point_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_landscape_points_snapshot_cluster", "snapshot_id", "cluster_id"),
    )
