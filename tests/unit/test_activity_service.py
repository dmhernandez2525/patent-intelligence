"""Tests for activity logging service."""

from unittest.mock import MagicMock

import pytest

from src.services.activity_service import activity_service


class _SessionWithAdd:
    def __init__(self) -> None:
        self.add = MagicMock()


@pytest.mark.asyncio
async def test_log_event_skips_when_session_has_no_add() -> None:
    class SessionWithoutAdd:
        pass

    await activity_service.log_event(SessionWithoutAdd(), event_type="search.query")


@pytest.mark.asyncio
async def test_log_event_adds_activity_record() -> None:
    session = _SessionWithAdd()
    await activity_service.log_event(session, event_type="auth.login", user_id=1)
    session.add.assert_called_once()
