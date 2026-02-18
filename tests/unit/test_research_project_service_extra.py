"""Additional unit tests for research project service."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.research_project import (
    ProjectPermission,
    ResearchProject,
    ResearchProjectMember,
    ResearchProjectPatent,
)
from src.services.research_project_service import ResearchProjectService

_OWN = ProjectPermission.OWNER.value
_EDIT = ProjectPermission.EDITOR.value
_VIEW = ProjectPermission.VIEWER.value


class _R:
    def __init__(self, val=None, rows=None):
        self._v = val
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._v

    def scalar(self):
        return self._v

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


def _svc():
    return ResearchProjectService()


def _session(add=True):
    s = AsyncMock()
    if add:
        s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


def _proj(**kw):
    defaults = {"id": 1, "name": "Lithium", "description": "R", "owner_id": 10}
    defaults.update(kw)
    p = ResearchProject(**defaults)
    p.members, p.patents = [], []
    return p


def _patch_perm(mp, svc, val):
    mp.setattr(svc, "_require_permission", AsyncMock(return_value=val))


def _patch_get(mp, svc, proj):
    mp.setattr(svc, "_get_project", AsyncMock(return_value=proj))


# ---- list_for_user ----

@pytest.mark.asyncio
async def test_list_for_user_returns_projects():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(rows=[_proj(name="A"), _proj(name="B")])
    r = await svc.list_for_user(s, user_id=10)
    assert len(r) == 2 and r[0].name == "A"

@pytest.mark.asyncio
async def test_list_for_user_empty():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(rows=[])
    assert await svc.list_for_user(s, user_id=99) == []

# ---- get_project ----

@pytest.mark.asyncio
async def test_get_project_success(monkeypatch):
    svc = _svc()
    proj = _proj(id=5, name="Quantum")
    _patch_get(monkeypatch, svc, proj)
    _patch_perm(monkeypatch, svc, _VIEW)
    r = await svc.get_project(AsyncMock(), 5, 2)
    assert r.id == 5 and r.name == "Quantum"

@pytest.mark.asyncio
async def test_get_project_not_found(monkeypatch):
    svc = _svc()
    monkeypatch.setattr(
        svc, "_get_project",
        AsyncMock(side_effect=ValueError("Project not found")),
    )
    with pytest.raises(ValueError, match="not found"):
        await svc.get_project(AsyncMock(), 999, 1)

@pytest.mark.asyncio
async def test_get_project_no_permission(monkeypatch):
    svc = _svc()
    _patch_get(monkeypatch, svc, _proj(id=5))
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(side_effect=PermissionError("Insufficient")),
    )
    with pytest.raises(PermissionError, match="Insufficient"):
        await svc.get_project(AsyncMock(), 5, 99)

# ---- update_project ----

@pytest.mark.asyncio
async def test_update_project_all_fields(monkeypatch):
    svc, s = _svc(), _session(add=False)
    proj = _proj(id=3, name="Old", description="Old")
    proj.status = "active"
    _patch_perm(monkeypatch, svc, _OWN)
    _patch_get(monkeypatch, svc, proj)
    r = await svc.update_project(s, 3, 10, "New", "New desc", "on_hold")
    assert r.name == "New" and r.description == "New desc"
    assert r.status == "on_hold"

@pytest.mark.asyncio
async def test_update_project_partial_fields(monkeypatch):
    svc, s = _svc(), _session(add=False)
    proj = _proj(id=3, name="Keep", description="Keep")
    proj.status = "active"
    _patch_perm(monkeypatch, svc, _EDIT)
    _patch_get(monkeypatch, svc, proj)
    r = await svc.update_project(s, 3, 2, None, None, "completed")
    assert r.name == "Keep" and r.status == "completed"

@pytest.mark.asyncio
async def test_update_project_no_permission(monkeypatch):
    svc = _svc()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(side_effect=PermissionError("Insufficient")),
    )
    with pytest.raises(PermissionError):
        await svc.update_project(AsyncMock(), 3, 99, "X", None, None)

# ---- delete_project ----

@pytest.mark.asyncio
async def test_delete_project_success(monkeypatch):
    svc, s = _svc(), AsyncMock()
    proj = _proj(id=4)
    _patch_perm(monkeypatch, svc, _OWN)
    _patch_get(monkeypatch, svc, proj)
    s.delete = AsyncMock()
    assert await svc.delete_project(s, 4, 10) is True
    s.delete.assert_called_once_with(proj)

@pytest.mark.asyncio
async def test_delete_project_not_found(monkeypatch):
    svc = _svc()
    _patch_perm(monkeypatch, svc, _OWN)
    monkeypatch.setattr(
        svc, "_get_project",
        AsyncMock(side_effect=ValueError("Project not found")),
    )
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_project(AsyncMock(), 999, 10)

@pytest.mark.asyncio
async def test_delete_project_no_permission(monkeypatch):
    svc = _svc()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(side_effect=PermissionError("Insufficient")),
    )
    with pytest.raises(PermissionError):
        await svc.delete_project(AsyncMock(), 4, 99)

# ---- add_member (success) ----

@pytest.mark.asyncio
async def test_add_member_new_viewer(monkeypatch):
    svc, s = _svc(), _session()
    _patch_perm(monkeypatch, svc, _OWN)
    s.execute.return_value = _R(val=None)
    m = await svc.add_member(s, 1, 10, 20, "viewer")
    assert m.project_id == 1 and m.permission == "viewer"
    s.add.assert_called_once()

# ---- remove_member ----

@pytest.mark.asyncio
async def test_remove_member_success(monkeypatch):
    svc, s = _svc(), AsyncMock()
    s.delete = AsyncMock()
    _patch_perm(monkeypatch, svc, _OWN)
    target = ResearchProjectMember(project_id=1, user_id=30, permission="viewer")
    s.execute.return_value = _R(val=target)
    assert await svc.remove_member(s, 1, 10, 30) is True
    s.delete.assert_called_once_with(target)

@pytest.mark.asyncio
async def test_remove_member_not_found(monkeypatch):
    svc, s = _svc(), AsyncMock()
    _patch_perm(monkeypatch, svc, _OWN)
    s.execute.return_value = _R(val=None)
    assert await svc.remove_member(s, 1, 10, 999) is False

# ---- add_patent (success) ----

@pytest.mark.asyncio
async def test_add_patent_success(monkeypatch):
    svc, s = _svc(), _session()
    _patch_perm(monkeypatch, svc, _OWN)
    s.execute.side_effect = [_R(val=None), _R(val=77)]
    item = await svc.add_patent(s, 1, 10, " us555 ")
    assert item.patent_number == "US555" and item.patent_id == 77
    s.add.assert_called_once()

# ---- remove_patent ----

@pytest.mark.asyncio
async def test_remove_patent_success(monkeypatch):
    svc, s = _svc(), AsyncMock()
    s.delete = AsyncMock()
    _patch_perm(monkeypatch, svc, _EDIT)
    target = ResearchProjectPatent(
        id=9, project_id=1, patent_number="US555", added_by_user_id=10,
    )
    s.execute.return_value = _R(val=target)
    assert await svc.remove_patent(s, 1, 10, "us555") is True
    s.delete.assert_called_once_with(target)

@pytest.mark.asyncio
async def test_remove_patent_not_found(monkeypatch):
    svc, s = _svc(), AsyncMock()
    _patch_perm(monkeypatch, svc, _OWN)
    s.execute.return_value = _R(val=None)
    assert await svc.remove_patent(s, 1, 10, "US000") is False

@pytest.mark.asyncio
async def test_get_project_internal_success():
    svc, s = _svc(), AsyncMock()
    proj = _proj(id=5)
    s.execute.return_value = _R(val=proj)
    assert (await svc._get_project(s, 5)).id == 5

@pytest.mark.asyncio
async def test_get_project_internal_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="not found"):
        await svc._get_project(s, 999)

@pytest.mark.asyncio
async def test_require_permission_internal_success():
    svc, s = _svc(), AsyncMock()
    m = ResearchProjectMember(project_id=1, user_id=5, permission="owner")
    s.execute.return_value = _R(val=m)
    assert await svc._require_permission(s, 1, 5, {"owner"}) == "owner"

@pytest.mark.asyncio
async def test_require_permission_internal_denied():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(PermissionError, match="Insufficient"):
        await svc._require_permission(s, 1, 99, {"owner"})

@pytest.mark.asyncio
async def test_add_member_invalid_permission(monkeypatch):
    svc, s = _svc(), AsyncMock()
    _patch_perm(monkeypatch, svc, _OWN)
    with pytest.raises(ValueError, match="editor or viewer"):
        await svc.add_member(s, 1, 10, 20, "admin")


@pytest.mark.asyncio
async def test_add_member_updates_existing(monkeypatch):
    svc, s = _svc(), _session()
    _patch_perm(monkeypatch, svc, _OWN)
    existing = ResearchProjectMember(
        project_id=1, user_id=20, permission="viewer",
    )
    s.execute.return_value = _R(val=existing)
    m = await svc.add_member(s, 1, 10, 20, "editor")
    assert m.permission == "editor"


@pytest.mark.asyncio
async def test_remove_member_editor_cannot_remove_editor(monkeypatch):
    svc, s = _svc(), AsyncMock()
    _patch_perm(monkeypatch, svc, _EDIT)
    target = ResearchProjectMember(
        project_id=1, user_id=30, permission="editor",
    )
    s.execute.return_value = _R(val=target)
    with pytest.raises(PermissionError, match="only remove viewer"):
        await svc.remove_member(s, 1, 2, 30)
