"""Tests for the LandscapeService."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.landscape import LandscapePoint, LandscapeSnapshot
from src.services.landscape_service import LandscapeService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return LandscapeService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete, s.get = (
        AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    return s

def _snapshot(sid=1, uid=10, name="Test", status="pending", **kw):
    snap = MagicMock(spec=LandscapeSnapshot)
    snap.id, snap.user_id, snap.name = sid, uid, name
    snap.description = kw.get("description")
    snap.reduction_method = kw.get("reduction_method", "umap")
    snap.cluster_method = kw.get("cluster_method", "kmeans")
    snap.num_clusters = kw.get("num_clusters", 5)
    snap.config = kw.get("config", {})
    snap.status, snap.error_message = status, None
    snap.patent_count, snap.computed_at = 0, None
    return snap

def _point(pid=1, sid=1, cluster_id=0, label="Cluster 0", x=1.0, y=2.0, meta=None):
    pt = MagicMock(spec=LandscapePoint)
    pt.id, pt.snapshot_id, pt.patent_id = pid, sid, pid
    pt.x, pt.y = x, y
    pt.cluster_id, pt.cluster_label = cluster_id, label
    pt.point_metadata = meta or {"assignee": "Corp", "cpc_codes": ["H01L"]}
    return pt

def _patent(pid=1, emb=None):
    return SimpleNamespace(
        id=pid, patent_number=f"US{pid}",
        title=f"Patent {pid}", assignee_organization="Corp",
        cpc_codes=["H01L21"], embedding=emb or [0.1] * 768)


# -- Snapshot CRUD --------------------------------------------------------

@pytest.mark.asyncio
async def test_list_snapshots_returns_list():
    sess, svc = _sess(), _svc()
    sess.execute.return_value = _R(rows=[_snapshot(sid=i) for i in range(3)])
    result = await svc.list_snapshots(sess, user_id=10)
    assert len(result) == 3
    sess.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_list_snapshots_empty():
    sess, svc = _sess(), _svc()
    sess.execute.return_value = _R(rows=[])
    assert await svc.list_snapshots(sess, user_id=10) == []

@pytest.mark.asyncio
async def test_get_snapshot_success(monkeypatch):
    sess, svc = _sess(), _svc()
    snap = _snapshot()
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=snap))
    assert await svc.get_snapshot(sess, snapshot_id=1, user_id=10) is snap

@pytest.mark.asyncio
async def test_get_snapshot_not_found(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(
        svc, "_get_user_snapshot",
        AsyncMock(side_effect=ValueError("Landscape snapshot not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.get_snapshot(sess, snapshot_id=99, user_id=10)

@pytest.mark.asyncio
async def test_create_snapshot_success():
    sess, svc = _sess(), _svc()
    await svc.create_snapshot(
        sess, user_id=10, name="My Landscape", description="desc",
        reduction_method="tsne", cluster_method="kmeans",
        num_clusters=8, config={"k": 1})
    sess.add.assert_called_once()
    sess.flush.assert_awaited_once()
    sess.refresh.assert_awaited_once()
    added = sess.add.call_args[0][0]
    assert added.name == "My Landscape"
    assert added.status == "pending"
    assert added.num_clusters == 8

@pytest.mark.asyncio
async def test_create_snapshot_defaults():
    sess, svc = _sess(), _svc()
    await svc.create_snapshot(sess, user_id=10, name="Default")
    added = sess.add.call_args[0][0]
    assert added.reduction_method == "umap"
    assert added.cluster_method == "kmeans"
    assert added.num_clusters == 5
    assert added.config == {}
    assert added.description is None

@pytest.mark.asyncio
async def test_delete_snapshot_success(monkeypatch):
    sess, svc = _sess(), _svc()
    snap = _snapshot()
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=snap))
    assert await svc.delete_snapshot(sess, snapshot_id=1, user_id=10) is True
    sess.delete.assert_awaited_once_with(snap)

@pytest.mark.asyncio
async def test_delete_snapshot_not_found(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(
        svc, "_get_user_snapshot",
        AsyncMock(side_effect=ValueError("Landscape snapshot not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_snapshot(sess, snapshot_id=99, user_id=10)


# -- Computation ----------------------------------------------------------

@pytest.mark.asyncio
async def test_compute_snapshot_success(monkeypatch):
    sess, svc = _sess(), _svc()
    snap = _snapshot(status="pending")
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=snap))
    patents = [_patent(pid=i, emb=[0.1 * i, 0.2 * i] + [0.0] * 766) for i in range(1, 6)]
    sess.execute.return_value = _R(rows=patents)
    result = await svc.compute_snapshot(sess, snapshot_id=1, user_id=10)
    assert result.status == "completed"
    assert result.patent_count == 5
    assert sess.add.call_count == 5

@pytest.mark.asyncio
async def test_compute_snapshot_too_few_patents(monkeypatch):
    sess, svc = _sess(), _svc()
    snap = _snapshot(status="pending")
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=snap))
    sess.execute.return_value = _R(rows=[_patent(pid=1), _patent(pid=2)])
    result = await svc.compute_snapshot(sess, snapshot_id=1, user_id=10)
    assert result.status == "failed"
    assert result.error_message == "Too few patents with embeddings"

@pytest.mark.asyncio
async def test_compute_snapshot_error(monkeypatch):
    sess, svc = _sess(), _svc()
    snap = _snapshot(status="pending")
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=snap))
    sess.execute.side_effect = RuntimeError("db down")
    result = await svc.compute_snapshot(sess, snapshot_id=1, user_id=10)
    assert result.status == "failed"
    assert result.error_message == "Computation failed unexpectedly"


# -- Points ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_points_returns_list(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=_snapshot()))
    sess.execute.return_value = _R(rows=[_point(pid=i) for i in range(4)])
    assert len(await svc.get_points(sess, snapshot_id=1, user_id=10)) == 4

@pytest.mark.asyncio
async def test_get_points_with_cluster_filter(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=_snapshot()))
    sess.execute.return_value = _R(rows=[_point(pid=1, cluster_id=2)])
    assert len(await svc.get_points(sess, snapshot_id=1, user_id=10, cluster_id=2)) == 1

@pytest.mark.asyncio
async def test_get_points_empty(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(svc, "_get_user_snapshot", AsyncMock(return_value=_snapshot()))
    sess.execute.return_value = _R(rows=[])
    assert await svc.get_points(sess, snapshot_id=1, user_id=10) == []


# -- Cluster summary ------------------------------------------------------

@pytest.mark.asyncio
async def test_get_cluster_summary(monkeypatch):
    sess, svc = _sess(), _svc()
    pts = [
        _point(pid=1, cluster_id=0, label="Cluster 0", x=1.0, y=2.0,
               meta={"assignee": "ACME", "cpc_codes": ["H01L"]}),
        _point(pid=2, cluster_id=0, label="Cluster 0", x=3.0, y=4.0,
               meta={"assignee": "ACME", "cpc_codes": ["H01L"]}),
        _point(pid=3, cluster_id=1, label="Cluster 1", x=5.0, y=6.0,
               meta={"assignee": "BigCo", "cpc_codes": ["G06F"]}),
    ]
    monkeypatch.setattr(svc, "get_points", AsyncMock(return_value=pts))
    result = await svc.get_cluster_summary(sess, snapshot_id=1, user_id=10)
    assert len(result) == 2
    c0 = next(s for s in result if s["cluster_id"] == 0)
    assert c0["count"] == 2
    assert c0["centroid"]["x"] == 2.0
    assert "ACME" in c0["top_assignees"]
    assert next(s for s in result if s["cluster_id"] == 1)["count"] == 1

@pytest.mark.asyncio
async def test_get_cluster_summary_empty(monkeypatch):
    sess, svc = _sess(), _svc()
    monkeypatch.setattr(svc, "get_points", AsyncMock(return_value=[]))
    assert await svc.get_cluster_summary(sess, snapshot_id=1, user_id=10) == []


# -- Dimension reduction stubs --------------------------------------------

def test_reduce_dimensions_umap():
    embs = [[0.5, 0.3] + [0.0] * 766, [0.2, 0.8] + [0.0] * 766]
    coords = LandscapeService._reduce_dimensions(embs, "umap")
    assert len(coords) == 2
    for x, y in coords:
        assert -50.0 <= x <= 50.0
        assert -50.0 <= y <= 50.0

def test_reduce_dimensions_tsne():
    embs = [[0.1, 0.9] + [0.0] * 766]
    coords = LandscapeService._reduce_dimensions(embs, "tsne")
    assert len(coords) == 1
    assert isinstance(coords[0], tuple)

def test_reduce_dimensions_returns_correct_count():
    embs = [[float(i)] * 10 for i in range(20)]
    assert len(LandscapeService._reduce_dimensions(embs, "umap")) == 20

def test_reduce_dimensions_clamps_values():
    coords = LandscapeService._reduce_dimensions([[100.0, -100.0] + [0.0] * 766], "umap")
    assert coords[0] == (50.0, -50.0)

def test_reduce_dimensions_empty_embedding():
    assert LandscapeService._reduce_dimensions([[]], "umap") == [(0.0, 0.0)]


# -- Clustering stubs -----------------------------------------------------

def test_cluster_points_kmeans():
    labels = LandscapeService._cluster_points([(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)], "kmeans", 2)
    assert len(labels) == 3
    assert set(labels).issubset({0, 1})

def test_cluster_points_returns_correct_count():
    coords = [(float(i), float(i)) for i in range(15)]
    assert len(LandscapeService._cluster_points(coords, "kmeans", 3)) == 15

def test_cluster_points_round_robin():
    labels = LandscapeService._cluster_points([(0.0, 0.0)] * 6, "kmeans", 3)
    assert labels == [0, 1, 2, 0, 1, 2]


# -- Label generation -----------------------------------------------------

def test_label_clusters_with_cpc():
    labels = LandscapeService._label_clusters(
        [_patent(1), _patent(2), _patent(3)], [0, 0, 1],
        [["H01L21"], ["H01L33"], ["G06F17"]])
    assert "H01L" in labels[0]
    assert "G06F" in labels[1]

def test_label_clusters_no_cpc():
    labels = LandscapeService._label_clusters([_patent(1)], [0], [[]])
    assert labels[0] == "Cluster 0: General"

def test_label_clusters_short_cpc_ignored():
    labels = LandscapeService._label_clusters([_patent(1)], [0], [["AB"]])
    assert labels[0] == "Cluster 0: General"


# -- Internal helpers -----------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_snapshot_success():
    sess, svc = _sess(), _svc()
    snap = _snapshot()
    sess.execute.return_value = _R(val=snap)
    assert await svc._get_user_snapshot(sess, snapshot_id=1, user_id=10) is snap

@pytest.mark.asyncio
async def test_get_user_snapshot_not_found():
    sess, svc = _sess(), _svc()
    sess.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Landscape snapshot not found"):
        await svc._get_user_snapshot(sess, snapshot_id=99, user_id=10)
