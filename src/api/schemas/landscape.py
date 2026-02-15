"""Schemas for patent landscape visualization API."""

from pydantic import BaseModel, Field

_REDUCTION_PATTERN = "^(tsne|umap|pca)$"
_CLUSTER_PATTERN = "^(kmeans|hdbscan|dbscan)$"


class SnapshotCreateRequest(BaseModel):
    """Request payload to create a landscape snapshot."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    reduction_method: str = Field(
        pattern=_REDUCTION_PATTERN, default="umap",
    )
    cluster_method: str = Field(
        pattern=_CLUSTER_PATTERN, default="kmeans",
    )
    num_clusters: int = Field(default=5, ge=2, le=20)
    config: dict = Field(default_factory=dict)


class ComputeRequest(BaseModel):
    """Request payload to trigger landscape computation."""

    patent_ids: list[int] | None = None
    cpc_filter: str | None = None
    assignee_filter: str | None = None
    max_patents: int = Field(default=500, ge=10, le=2000)


class SnapshotResponse(BaseModel):
    """Landscape snapshot response model."""

    id: int
    user_id: int
    name: str
    description: str | None
    reduction_method: str
    cluster_method: str
    num_clusters: int
    patent_count: int
    status: str
    error_message: str | None
    computed_at: str | None
    created_at: str | None


class SnapshotListResponse(BaseModel):
    """Response for listing landscape snapshots."""

    snapshots: list[SnapshotResponse]


class PointResponse(BaseModel):
    """A single patent point in the landscape projection."""

    id: int
    patent_id: int
    x: float
    y: float
    cluster_id: int | None
    cluster_label: str | None
    metadata: dict


class PointListResponse(BaseModel):
    """Response for listing landscape points."""

    points: list[PointResponse]
    total: int


class ClusterSummary(BaseModel):
    """Summary statistics for a single cluster."""

    cluster_id: int
    label: str
    count: int
    centroid_x: float
    centroid_y: float
    top_assignees: list[str]


class ClusterSummaryResponse(BaseModel):
    """Response for cluster summary endpoint."""

    clusters: list[ClusterSummary]
