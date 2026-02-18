"""Tests for landscape API routes."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import landscape as mod


def _user(uid=1):
    return SimpleNamespace(id=uid, email="u@test.com", role="analyst")


def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


def _req():
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"User-Agent": "test"})


def _snapshot(sid=1, uid=1):
    return SimpleNamespace(
        id=sid, user_id=uid, name=f"Snapshot {sid}",
        description="Test snapshot", reduction_method="umap",
        cluster_method="kmeans", num_clusters=5, patent_count=100,
        status="completed", error_message=None,
        computed_at=datetime(2026, 1, 1, 12, 0, 0),
        created_at=datetime(2026, 1, 1, 10, 0, 0))


def _point(pid=1, sid=1, cid=0):
    return SimpleNamespace(
        id=pid, patent_id=100 + pid, snapshot_id=sid,
        x=1.0, y=2.0, cluster_id=cid, cluster_label="Cluster 0",
        point_metadata={"patent_number": "US100", "title": "Test"})


def _patch(mp, name, rv=None, exc=None):
    m = AsyncMock(side_effect=exc, return_value=rv)
    mp.setattr(mod, "landscape_service", SimpleNamespace(**{name: m}))
    return m


def _patch_act(mp):
    m = AsyncMock()
    mp.setattr(mod, "activity_service", SimpleNamespace(log_event=m))
    return m


async def _assert_http(coro, code):
    with pytest.raises(HTTPException) as ei:
        await coro
    assert ei.value.status_code == code


# ---- Snapshot list ----

@pytest.mark.asyncio
async def test_list_snapshots(monkeypatch):
    snaps = [_snapshot(1), _snapshot(2)]
    _patch(mp=monkeypatch, name="list_snapshots", rv=snaps)
    r = await mod.list_snapshots(current_user=_user(), session=_session())
    assert len(r.snapshots) == 2
    assert r.snapshots[0].id == 1 and r.snapshots[1].id == 2


@pytest.mark.asyncio
async def test_list_snapshots_empty(monkeypatch):
    _patch(mp=monkeypatch, name="list_snapshots", rv=[])
    r = await mod.list_snapshots(current_user=_user(), session=_session())
    assert r.snapshots == []


@pytest.mark.asyncio
async def test_list_snapshots_passes_user_id(monkeypatch):
    mock = _patch(mp=monkeypatch, name="list_snapshots", rv=[])
    await mod.list_snapshots(current_user=_user(uid=7), session=_session())
    assert mock.call_args.kwargs["user_id"] == 7


# ---- Snapshot create ----

@pytest.mark.asyncio
async def test_create_snapshot(monkeypatch):
    _patch(mp=monkeypatch, name="create_snapshot", rv=_snapshot(5))
    _patch_act(monkeypatch)
    payload = mod.SnapshotCreateRequest(name="New Landscape")
    r = await mod.create_snapshot(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5 and r.name == "Snapshot 5"


@pytest.mark.asyncio
async def test_create_snapshot_logs_activity(monkeypatch):
    _patch(mp=monkeypatch, name="create_snapshot", rv=_snapshot(6))
    act = _patch_act(monkeypatch)
    payload = mod.SnapshotCreateRequest(name="Logged")
    await mod.create_snapshot(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "landscape.snapshot.created"
    assert kw["resource_type"] == "landscape_snapshot"
    assert kw["resource_id"] == "6"


# ---- Snapshot get ----

@pytest.mark.asyncio
async def test_get_snapshot(monkeypatch):
    _patch(mp=monkeypatch, name="get_snapshot", rv=_snapshot(3))
    r = await mod.get_snapshot(
        snapshot_id=3, current_user=_user(), session=_session())
    assert r.id == 3 and r.reduction_method == "umap"


@pytest.mark.asyncio
async def test_get_snapshot_not_found(monkeypatch):
    _patch(mp=monkeypatch, name="get_snapshot", exc=ValueError("not found"))
    await _assert_http(
        mod.get_snapshot(snapshot_id=999, current_user=_user(),
                         session=_session()), 404)


@pytest.mark.asyncio
async def test_get_snapshot_response_fields(monkeypatch):
    _patch(mp=monkeypatch, name="get_snapshot", rv=_snapshot(1))
    r = await mod.get_snapshot(
        snapshot_id=1, current_user=_user(), session=_session())
    assert r.cluster_method == "kmeans" and r.num_clusters == 5
    assert r.patent_count == 100 and r.computed_at is not None

@pytest.mark.asyncio
async def test_delete_snapshot(monkeypatch):
    _patch(mp=monkeypatch, name="delete_snapshot", rv=True)
    _patch_act(monkeypatch)
    r = await mod.delete_snapshot(
        snapshot_id=1, request=_req(),
        current_user=_user(), session=_session())
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_snapshot_not_found(monkeypatch):
    _patch(mp=monkeypatch, name="delete_snapshot",
           exc=ValueError("not found"))
    _patch_act(monkeypatch)
    await _assert_http(
        mod.delete_snapshot(snapshot_id=999, request=_req(),
                            current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_delete_snapshot_logs_activity(monkeypatch):
    _patch(mp=monkeypatch, name="delete_snapshot", rv=True)
    act = _patch_act(monkeypatch)
    await mod.delete_snapshot(
        snapshot_id=4, request=_req(),
        current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "landscape.snapshot.deleted"
    assert kw["resource_type"] == "landscape_snapshot"
    assert kw["resource_id"] == "4"

@pytest.mark.asyncio
async def test_compute_snapshot(monkeypatch):
    _patch(mp=monkeypatch, name="compute_snapshot", rv=_snapshot(2))
    _patch_act(monkeypatch)
    payload = mod.ComputeRequest(patent_ids=[1, 2, 3])
    r = await mod.compute_snapshot(
        snapshot_id=2, payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 2 and r.status == "completed"


@pytest.mark.asyncio
async def test_compute_snapshot_not_found(monkeypatch):
    _patch(mp=monkeypatch, name="compute_snapshot",
           exc=ValueError("snapshot not found"))
    _patch_act(monkeypatch)
    payload = mod.ComputeRequest()
    await _assert_http(
        mod.compute_snapshot(snapshot_id=999, payload=payload,
                             request=_req(), current_user=_user(),
                             session=_session()), 404)


@pytest.mark.asyncio
async def test_compute_snapshot_logs_activity(monkeypatch):
    _patch(mp=monkeypatch, name="compute_snapshot", rv=_snapshot(8))
    act = _patch_act(monkeypatch)
    payload = mod.ComputeRequest(max_patents=200)
    await mod.compute_snapshot(
        snapshot_id=8, payload=payload, request=_req(),
        current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "landscape.snapshot.computed"
    assert kw["resource_id"] == "8"
    assert kw["event_metadata"]["max_patents"] == 200

@pytest.mark.asyncio
async def test_get_points(monkeypatch):
    pts = [_point(1), _point(2)]
    _patch(mp=monkeypatch, name="get_points", rv=pts)
    r = await mod.list_points(
        snapshot_id=1, cluster_id=None,
        current_user=_user(), session=_session())
    assert r.total == 2
    assert r.points[0].patent_id == 101 and r.points[1].patent_id == 102


@pytest.mark.asyncio
async def test_get_points_with_cluster_filter(monkeypatch):
    mock = _patch(mp=monkeypatch, name="get_points", rv=[_point(3, cid=2)])
    r = await mod.list_points(
        snapshot_id=1, cluster_id=2,
        current_user=_user(), session=_session())
    assert r.total == 1 and mock.call_args.kwargs["cluster_id"] == 2


@pytest.mark.asyncio
async def test_get_points_not_found(monkeypatch):
    _patch(mp=monkeypatch, name="get_points",
           exc=ValueError("snapshot not found"))
    await _assert_http(
        mod.list_points(snapshot_id=999, cluster_id=None,
                        current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_get_points_metadata(monkeypatch):
    _patch(mp=monkeypatch, name="get_points", rv=[_point(1)])
    r = await mod.list_points(
        snapshot_id=1, cluster_id=None,
        current_user=_user(), session=_session())
    assert r.points[0].metadata["patent_number"] == "US100"
    assert r.points[0].metadata["title"] == "Test"

@pytest.mark.asyncio
async def test_get_clusters(monkeypatch):
    clusters = [
        {"cluster_id": 0, "label": "Cluster 0: H01L", "count": 5,
         "centroid": {"x": 1.0, "y": 2.0}, "top_assignees": ["Corp"]},
        {"cluster_id": 1, "label": "Cluster 1: G06F", "count": 3,
         "centroid": {"x": 3.0, "y": 4.0}, "top_assignees": ["Inc"]},
    ]
    _patch(mp=monkeypatch, name="get_cluster_summary", rv=clusters)
    r = await mod.list_clusters(
        snapshot_id=1, current_user=_user(), session=_session())
    assert len(r.clusters) == 2
    assert r.clusters[0].cluster_id == 0
    assert r.clusters[0].label == "Cluster 0: H01L"
    assert r.clusters[0].count == 5
    assert r.clusters[0].centroid_x == 1.0 and r.clusters[0].centroid_y == 2.0
    assert r.clusters[0].top_assignees == ["Corp"]
    assert r.clusters[1].cluster_id == 1


@pytest.mark.asyncio
async def test_get_clusters_not_found(monkeypatch):
    _patch(mp=monkeypatch, name="get_cluster_summary",
           exc=ValueError("snapshot not found"))
    await _assert_http(
        mod.list_clusters(snapshot_id=999, current_user=_user(),
                          session=_session()), 404)


@pytest.mark.asyncio
async def test_get_clusters_empty(monkeypatch):
    _patch(mp=monkeypatch, name="get_cluster_summary", rv=[])
    r = await mod.list_clusters(
        snapshot_id=1, current_user=_user(), session=_session())
    assert r.clusters == []
