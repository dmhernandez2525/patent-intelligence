"""Unit tests for team activity feed service."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.user import UserActivityLog
from src.services.team_activity_service import team_activity_service


class _Result:
    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


@pytest.mark.asyncio
async def test_get_feed_aggregates_team_members() -> None:
    session = AsyncMock()
    event = UserActivityLog(
        id=1,
        user_id=9,
        event_type="collaboration.project.created",
        resource_type="research_project",
        resource_id="12",
    )
    event.created_at = datetime.now(UTC)
    session.execute.side_effect = [_Result(rows=[(9,), (10,)]), _Result(rows=[event])]

    rows = await team_activity_service.get_feed(session, user_id=9, limit=10)

    assert len(rows) == 1
    assert rows[0]["event_type"] == "collaboration.project.created"
