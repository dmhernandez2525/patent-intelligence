"""Unit tests for research project collaboration service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.patent import Patent
from src.models.research_project import (
    ProjectPermission,
    ResearchProjectMember,
    ResearchProjectPatent,
)
from src.services.research_project_service import research_project_service


class _Result:
    def __init__(self, scalar_value=None, rows=None):
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


@pytest.mark.asyncio
async def test_create_project_adds_owner_membership() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    project = await research_project_service.create_project(
        session,
        owner_id=10,
        name="Battery Program",
        description="Phase A",
    )

    assert project.owner_id == 10
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_add_member_editor_cannot_promote_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        research_project_service,
        "_require_permission",
        AsyncMock(return_value=ProjectPermission.EDITOR.value),
    )

    with pytest.raises(PermissionError, match="cannot promote"):
        await research_project_service.add_member(
            session,
            project_id=1,
            actor_user_id=2,
            member_user_id=3,
            permission="editor",
        )


@pytest.mark.asyncio
async def test_remove_member_prevents_owner_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        research_project_service,
        "_require_permission",
        AsyncMock(return_value=ProjectPermission.OWNER.value),
    )
    owner_member = ResearchProjectMember(project_id=1, user_id=1, permission="owner")
    session.execute.return_value = _Result(scalar_value=owner_member)

    with pytest.raises(PermissionError, match="cannot be removed"):
        await research_project_service.remove_member(
            session,
            project_id=1,
            actor_user_id=1,
            member_user_id=1,
        )


@pytest.mark.asyncio
async def test_scoped_search_returns_matching_patents(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        research_project_service,
        "_require_permission",
        AsyncMock(return_value=ProjectPermission.VIEWER.value),
    )
    patent = Patent(
        id=3,
        patent_number="US123",
        title="Battery Cell",
        abstract="Energy storage",
        status="active",
        country="US",
        citation_count=0,
        cited_by_count=0,
        claim_count=0,
        patent_term_adjustment_days=0,
        patent_term_extension_days=0,
        terminal_disclaimer=False,
        source="uspto",
    )
    session.execute.side_effect = [_Result(scalar_value=1), _Result(rows=[patent])]

    rows, total = await research_project_service.scoped_search(
        session,
        project_id=1,
        user_id=4,
        query="battery",
        page=1,
        per_page=20,
    )

    assert total == 1
    assert rows[0]["patent_number"] == "US123"


@pytest.mark.asyncio
async def test_add_patent_rejects_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        research_project_service,
        "_require_permission",
        AsyncMock(return_value=ProjectPermission.EDITOR.value),
    )
    session.execute.return_value = _Result(
        scalar_value=ResearchProjectPatent(
            id=2,
            project_id=1,
            patent_number="US123",
            added_by_user_id=1,
        )
    )

    with pytest.raises(ValueError, match="already exists"):
        await research_project_service.add_patent(
            session,
            project_id=1,
            actor_user_id=1,
            patent_number="US123",
        )
