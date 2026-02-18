"""Unit tests for collaboration project routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import collaboration_projects as mod
from src.models.research_project import (
    ResearchProject,
    ResearchProjectMember,
    ResearchProjectPatent,
)
from src.models.user import User

_SVC = "research_project_service"
_ACT = "activity_service"


def _user() -> User:
    return User(
        id=1, email="t@example.com",
        hashed_password="".join(["h", "x"]),
        role="analyst", is_active=True,
    )


def _req() -> Request:
    return Request({
        "type": "http", "method": "POST", "path": "/",
        "headers": [], "client": ("127.0.0.1", 7777),
    })


def _project(pid: int = 1) -> ResearchProject:
    p = ResearchProject(
        id=pid, name="Proj", description="d",
        status="active", owner_id=1,
    )
    p.members = [ResearchProjectMember(
        id=1, project_id=pid, user_id=1, permission="owner",
    )]
    p.patents = [ResearchProjectPatent(
        id=10, project_id=pid, patent_number="US123",
        patent_id=99, added_by_user_id=1,
    )]
    return p


def _patch(mp, method, val=None, exc=None):
    m = AsyncMock(side_effect=exc, return_value=val)
    mp.setattr(getattr(mod, _SVC), method, m)
    return m


def _patch_act(mp):
    mp.setattr(getattr(mod, _ACT), "log_event", AsyncMock())


def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


async def _assert_http(coro, code):
    with pytest.raises(HTTPException) as ei:
        await coro
    assert ei.value.status_code == code


@pytest.mark.asyncio
async def test_list_projects(monkeypatch):
    _patch(monkeypatch, "list_for_user", [_project()])
    r = await mod.list_projects(
        current_user=_user(), session=_session(),
    )
    assert len(r.projects) == 1
    assert r.projects[0].name == "Proj"


@pytest.mark.asyncio
async def test_create_project(monkeypatch):
    proj = _project(5)
    _patch(monkeypatch, "create_project", proj)
    _patch(monkeypatch, "get_project", proj)
    _patch_act(monkeypatch)
    payload = mod.ProjectCreateRequest(name="New")
    r = await mod.create_project(
        payload=payload, request=_req(),
        current_user=_user(), session=_session(),
    )
    assert r.id == 5


@pytest.mark.asyncio
async def test_get_project_success(monkeypatch):
    _patch(monkeypatch, "get_project", _project(2))
    r = await mod.get_project(
        project_id=2, current_user=_user(),
        session=_session(),
    )
    assert r.id == 2


@pytest.mark.asyncio
async def test_get_project_errors(monkeypatch):
    s = _session()
    _patch(monkeypatch, "get_project", exc=ValueError("x"))
    await _assert_http(
        mod.get_project(99, current_user=_user(), session=s),
        404,
    )
    _patch(monkeypatch, "get_project", exc=PermissionError("x"))
    await _assert_http(
        mod.get_project(1, current_user=_user(), session=s),
        403,
    )


@pytest.mark.asyncio
async def test_update_project_success(monkeypatch):
    _patch(monkeypatch, "update_project", _project())
    _patch_act(monkeypatch)
    payload = mod.ProjectUpdateRequest(name="Up")
    r = await mod.update_project(
        project_id=1, payload=payload,
        current_user=_user(), session=_session(),
    )
    assert r.name == "Proj"


@pytest.mark.asyncio
async def test_update_project_errors(monkeypatch):
    s, pl = _session(), mod.ProjectUpdateRequest(name="X")
    _patch(monkeypatch, "update_project", exc=ValueError("x"))
    await _assert_http(
        mod.update_project(1, pl, current_user=_user(), session=s),
        404,
    )
    _patch(monkeypatch, "update_project", exc=PermissionError("x"))
    await _assert_http(
        mod.update_project(1, pl, current_user=_user(), session=s),
        403,
    )


@pytest.mark.asyncio
async def test_delete_project_success(monkeypatch):
    _patch(monkeypatch, "delete_project", None)
    _patch_act(monkeypatch)
    r = await mod.delete_project(
        project_id=1, current_user=_user(), session=_session(),
    )
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_project_errors(monkeypatch):
    s = _session()
    _patch(monkeypatch, "delete_project", exc=ValueError("x"))
    await _assert_http(
        mod.delete_project(1, current_user=_user(), session=s),
        404,
    )
    _patch(monkeypatch, "delete_project", exc=PermissionError("x"))
    await _assert_http(
        mod.delete_project(1, current_user=_user(), session=s),
        403,
    )


@pytest.mark.asyncio
async def test_add_member_success(monkeypatch):
    member = ResearchProjectMember(
        id=2, project_id=1, user_id=3, permission="editor",
    )
    _patch(monkeypatch, "add_member", member)
    _patch_act(monkeypatch)
    pl = mod.ProjectMemberRequest(user_id=3, permission="editor")
    r = await mod.add_project_member(
        project_id=1, payload=pl,
        current_user=_user(), session=_session(),
    )
    assert r.user_id == 3 and r.permission == "editor"


@pytest.mark.asyncio
async def test_add_member_errors(monkeypatch):
    s = _session()
    pl = mod.ProjectMemberRequest(user_id=3, permission="editor")
    _patch(monkeypatch, "add_member", exc=ValueError("x"))
    await _assert_http(
        mod.add_project_member(1, pl, current_user=_user(), session=s),
        400,
    )
    _patch(monkeypatch, "add_member", exc=PermissionError("x"))
    await _assert_http(
        mod.add_project_member(1, pl, current_user=_user(), session=s),
        403,
    )


@pytest.mark.asyncio
async def test_remove_member(monkeypatch):
    _patch(monkeypatch, "remove_member", True)
    _patch_act(monkeypatch)
    r = await mod.remove_project_member(
        project_id=1, member_user_id=2,
        current_user=_user(), session=_session(),
    )
    assert r == {"success": True}
    # not found
    _patch(monkeypatch, "remove_member", False)
    await _assert_http(mod.remove_project_member(
        1, 2, current_user=_user(), session=_session(),
    ), 404)
    # forbidden
    _patch(monkeypatch, "remove_member", exc=PermissionError("x"))
    await _assert_http(mod.remove_project_member(
        1, 2, current_user=_user(), session=_session(),
    ), 403)


@pytest.mark.asyncio
async def test_add_patent_success(monkeypatch):
    pat = ResearchProjectPatent(
        id=7, project_id=1, patent_number="US456",
        patent_id=None, added_by_user_id=1,
    )
    _patch(monkeypatch, "add_patent", pat)
    _patch_act(monkeypatch)
    pl = mod.ProjectPatentRequest(patent_number="US456")
    r = await mod.add_project_patent(
        project_id=1, payload=pl,
        current_user=_user(), session=_session(),
    )
    assert r.patent_number == "US456" and r.id == 7


@pytest.mark.asyncio
async def test_add_patent_errors(monkeypatch):
    s = _session()
    pl = mod.ProjectPatentRequest(patent_number="US456")
    _patch(monkeypatch, "add_patent", exc=ValueError("x"))
    await _assert_http(
        mod.add_project_patent(1, pl, current_user=_user(), session=s),
        400,
    )
    _patch(monkeypatch, "add_patent", exc=PermissionError("x"))
    await _assert_http(
        mod.add_project_patent(1, pl, current_user=_user(), session=s),
        403,
    )


@pytest.mark.asyncio
async def test_remove_patent(monkeypatch):
    _patch(monkeypatch, "remove_patent", True)
    _patch_act(monkeypatch)
    r = await mod.remove_project_patent(
        project_id=1, patent_number="US123",
        current_user=_user(), session=_session(),
    )
    assert r == {"success": True}
    # not found
    _patch(monkeypatch, "remove_patent", False)
    await _assert_http(mod.remove_project_patent(
        1, "US999", current_user=_user(), session=_session(),
    ), 404)
    # forbidden
    _patch(monkeypatch, "remove_patent", exc=PermissionError("x"))
    await _assert_http(mod.remove_project_patent(
        1, "US123", current_user=_user(), session=_session(),
    ), 403)


@pytest.mark.asyncio
async def test_scoped_search(monkeypatch):
    patents = [{
        "id": 1, "patent_number": "US123", "title": "W",
        "status": "granted", "country": "US",
        "filing_date": "2024-01-01",
    }]
    _patch(monkeypatch, "scoped_search", (patents, 1))
    pl = mod.ProjectSearchRequest(query="widget")
    r = await mod.scoped_project_search(
        project_id=1, payload=pl,
        current_user=_user(), session=_session(),
    )
    assert r.total == 1
    assert r.patents[0].patent_number == "US123"
    # forbidden
    _patch(monkeypatch, "scoped_search", exc=PermissionError("x"))
    await _assert_http(mod.scoped_project_search(
        1, mod.ProjectSearchRequest(query="t"),
        current_user=_user(), session=_session(),
    ), 403)
