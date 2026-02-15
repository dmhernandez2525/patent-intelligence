"""Patent landscape visualization and clustering service."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.landscape import LandscapePoint, LandscapeSnapshot
from src.models.patent import Patent

logger = structlog.get_logger(__name__)


class LandscapeService:
    """Service for patent landscape visualization and clustering."""

    async def list_snapshots(
        self, session: AsyncSession, user_id: int,
    ) -> list[LandscapeSnapshot]:
        result = await session.execute(
            select(LandscapeSnapshot)
            .where(LandscapeSnapshot.user_id == user_id)
            .order_by(LandscapeSnapshot.created_at.desc()))
        return list(result.scalars().all())

    async def get_snapshot(
        self, session: AsyncSession, snapshot_id: int, user_id: int,
    ) -> LandscapeSnapshot:
        return await self._get_user_snapshot(session, snapshot_id, user_id)

    async def create_snapshot(
        self, session: AsyncSession, user_id: int,
        name: str, description: str | None = None,
        reduction_method: str = "umap",
        cluster_method: str = "kmeans",
        num_clusters: int = 5,
        config: dict | None = None,
    ) -> LandscapeSnapshot:
        snapshot = LandscapeSnapshot(
            user_id=user_id, name=name,
            description=description,
            reduction_method=reduction_method,
            cluster_method=cluster_method,
            num_clusters=num_clusters,
            config=config or {},
            status="pending")
        session.add(snapshot)
        await session.flush()
        await session.refresh(snapshot)
        return snapshot

    async def compute_snapshot(
        self, session: AsyncSession,
        snapshot_id: int, user_id: int,
        patent_ids: list[int] | None = None,
        cpc_filter: str | None = None,
        assignee_filter: str | None = None,
        max_patents: int = 500,
    ) -> LandscapeSnapshot:
        snapshot = await self._get_user_snapshot(
            session, snapshot_id, user_id)
        snapshot.status = "computing"

        try:
            conditions: list = [Patent.embedding.isnot(None)]
            if patent_ids:
                conditions.append(Patent.id.in_(patent_ids))
            if cpc_filter:
                conditions.append(
                    Patent.cpc_codes.contains([cpc_filter]))
            if assignee_filter:
                conditions.append(
                    Patent.assignee_organization == assignee_filter)

            query = (
                select(Patent)
                .where(and_(*conditions))
                .limit(max_patents))
            result = await session.execute(query)
            patents = list(result.scalars().all())

            embeddings = [
                list(p.embedding) for p in patents]  # type: ignore[arg-type]

            if len(patents) < 3:
                snapshot.status = "failed"
                snapshot.error_message = (
                    "Too few patents with embeddings")
                await session.flush()
                return snapshot

            coords_2d = self._reduce_dimensions(
                embeddings, snapshot.reduction_method,
                snapshot.config)

            cluster_assignments = self._cluster_points(
                coords_2d, snapshot.cluster_method,
                snapshot.num_clusters)

            all_cpc: list[list[str]] = [
                p.cpc_codes or [] for p in patents]
            cluster_labels = self._label_clusters(
                patents, cluster_assignments, all_cpc)

            for i, patent in enumerate(patents):
                x, y = coords_2d[i]
                cid = cluster_assignments[i]
                point = LandscapePoint(
                    snapshot_id=snapshot.id,
                    patent_id=patent.id,
                    x=x, y=y,
                    cluster_id=cid,
                    cluster_label=cluster_labels.get(cid, f"Cluster {cid}"),
                    point_metadata={
                        "patent_number": patent.patent_number,
                        "title": patent.title,
                        "assignee": patent.assignee_organization,
                        "cpc_codes": patent.cpc_codes or [],
                    })
                session.add(point)

            snapshot.status = "completed"
            snapshot.patent_count = len(patents)
            snapshot.computed_at = datetime.now(UTC)

        except Exception:
            logger.exception("snapshot_compute_failed",
                             snapshot_id=snapshot_id)
            snapshot.status = "failed"
            snapshot.error_message = "Computation failed unexpectedly"

        await session.flush()
        return snapshot

    async def get_points(
        self, session: AsyncSession,
        snapshot_id: int, user_id: int,
        cluster_id: int | None = None,
    ) -> list[LandscapePoint]:
        await self._get_user_snapshot(session, snapshot_id, user_id)
        conditions = [
            LandscapePoint.snapshot_id == snapshot_id]
        if cluster_id is not None:
            conditions.append(
                LandscapePoint.cluster_id == cluster_id)
        result = await session.execute(
            select(LandscapePoint)
            .where(and_(*conditions)))
        return list(result.scalars().all())

    async def get_cluster_summary(
        self, session: AsyncSession,
        snapshot_id: int, user_id: int,
    ) -> list[dict]:
        points = await self.get_points(
            session, snapshot_id, user_id)

        clusters: dict[int, list[LandscapePoint]] = {}
        for pt in points:
            cid = pt.cluster_id if pt.cluster_id is not None else -1
            clusters.setdefault(cid, []).append(pt)

        summaries = []
        for cid, cpts in sorted(clusters.items()):
            avg_x = sum(p.x for p in cpts) / len(cpts)
            avg_y = sum(p.y for p in cpts) / len(cpts)
            assignees: list[str] = []
            for p in cpts:
                a = (p.point_metadata or {}).get("assignee")
                if a:
                    assignees.append(a)
            top_assignees = [
                name for name, _ in Counter(assignees).most_common(5)]
            summaries.append({
                "cluster_id": cid,
                "count": len(cpts),
                "label": cpts[0].cluster_label or f"Cluster {cid}",
                "centroid": {"x": round(avg_x, 4), "y": round(avg_y, 4)},
                "top_assignees": top_assignees,
            })
        return summaries

    async def delete_snapshot(
        self, session: AsyncSession,
        snapshot_id: int, user_id: int,
    ) -> bool:
        snapshot = await self._get_user_snapshot(
            session, snapshot_id, user_id)
        await session.delete(snapshot)
        return True

    @staticmethod
    def _reduce_dimensions(
        embeddings: list[list[float]],
        method: str,
        config: dict | None = None,
    ) -> list[tuple[float, float]]:
        """Reduce high-dimensional embeddings to 2D coordinates.

        Stub implementation using a simple projection of the first
        two dimensions. Production would use sklearn UMAP or t-SNE.
        """
        logger.info("reduce_dimensions",
                     method=method, count=len(embeddings))
        coords: list[tuple[float, float]] = []
        for emb in embeddings:
            raw_x = emb[0] if len(emb) > 0 else 0.0
            raw_y = emb[1] if len(emb) > 1 else 0.0
            x = max(-50.0, min(50.0, raw_x * 50.0))
            y = max(-50.0, min(50.0, raw_y * 50.0))
            coords.append((round(x, 4), round(y, 4)))
        return coords

    @staticmethod
    def _cluster_points(
        coords: list[tuple[float, float]],
        method: str,
        num_clusters: int,
    ) -> list[int]:
        """Assign each point to a cluster.

        Stub implementation using round-robin assignment.
        Production would use sklearn KMeans or HDBSCAN.
        """
        logger.info("cluster_points",
                     method=method, num_clusters=num_clusters)
        return [i % num_clusters for i in range(len(coords))]

    @staticmethod
    def _label_clusters(
        patents: list[Patent],
        assignments: list[int],
        all_cpc: list[list[str]],
    ) -> dict[int, str]:
        """Generate a label for each cluster based on CPC codes."""
        cluster_cpc: dict[int, list[str]] = {}
        for i, cid in enumerate(assignments):
            cluster_cpc.setdefault(cid, [])
            for code in all_cpc[i]:
                if len(code) >= 4:
                    cluster_cpc[cid].append(code[:4])

        labels: dict[int, str] = {}
        for cid, prefixes in cluster_cpc.items():
            if prefixes:
                most_common = Counter(prefixes).most_common(1)[0][0]
                labels[cid] = f"Cluster {cid}: {most_common}"
            else:
                labels[cid] = f"Cluster {cid}: General"
        return labels

    async def _get_user_snapshot(
        self, session: AsyncSession,
        snapshot_id: int, user_id: int,
    ) -> LandscapeSnapshot:
        r = await session.execute(
            select(LandscapeSnapshot).where(and_(
                LandscapeSnapshot.id == snapshot_id,
                LandscapeSnapshot.user_id == user_id)))
        snap = r.scalar_one_or_none()
        if snap is None:
            raise ValueError("Landscape snapshot not found")
        return snap


landscape_service = LandscapeService()
