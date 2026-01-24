"""Unit tests for watchlist service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.services.watchlist_service import WatchlistService
from src.models.watchlist import WatchlistItem, Alert


@pytest.fixture
def watchlist_service():
    return WatchlistService()


class TestWatchlistService:
    """Tests for WatchlistService."""

    @pytest.mark.asyncio
    async def test_get_watchlist_empty(self, watchlist_service):
        """Test getting empty watchlist."""
        mock_session = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_items_result]

        items, total = await watchlist_service.get_watchlist(mock_session)

        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_alerts_empty(self, watchlist_service):
        """Test getting empty alerts."""
        mock_session = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_alerts_result = MagicMock()
        mock_alerts_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_alerts_result]

        alerts, total = await watchlist_service.get_alerts(mock_session)

        assert alerts == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_alert_summary_empty(self, watchlist_service):
        """Test alert summary with no alerts."""
        mock_session = AsyncMock()
        mock_type_result = MagicMock()
        mock_type_result.all.return_value = []

        mock_priority_result = MagicMock()
        mock_priority_result.all.return_value = []

        mock_session.execute.side_effect = [mock_type_result, mock_priority_result]

        summary = await watchlist_service.get_alert_summary(mock_session)

        assert summary["total_unread"] == 0
        assert summary["by_type"] == {}
        assert summary["critical_count"] == 0

    def test_to_watchlist_dict(self, watchlist_service):
        """Test watchlist item conversion to dict."""
        item = MagicMock(spec=WatchlistItem)
        item.id = 1
        item.item_type = "patent"
        item.item_value = "US12345678"
        item.patent_id = 100
        item.name = "Test Patent"
        item.notes = "Some notes"
        item.notify_expiration = True
        item.notify_maintenance = True
        item.notify_citations = False
        item.notify_new_patents = False
        item.expiration_lead_days = 90
        item.maintenance_lead_days = 30
        item.is_active = True
        item.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        item.alerts = []

        result = watchlist_service._to_watchlist_dict(item)

        assert result["id"] == 1
        assert result["item_type"] == "patent"
        assert result["item_value"] == "US12345678"
        assert result["name"] == "Test Patent"
        assert result["unread_alerts"] == 0

    def test_to_watchlist_dict_with_alerts(self, watchlist_service):
        """Test watchlist item with unread alerts."""
        alert1 = MagicMock(spec=Alert)
        alert1.is_read = False
        alert1.is_dismissed = False

        alert2 = MagicMock(spec=Alert)
        alert2.is_read = True
        alert2.is_dismissed = False

        item = MagicMock(spec=WatchlistItem)
        item.id = 1
        item.item_type = "patent"
        item.item_value = "US12345678"
        item.patent_id = 100
        item.name = None
        item.notes = None
        item.notify_expiration = True
        item.notify_maintenance = True
        item.notify_citations = False
        item.notify_new_patents = False
        item.expiration_lead_days = 90
        item.maintenance_lead_days = 30
        item.is_active = True
        item.created_at = None
        item.alerts = [alert1, alert2]

        result = watchlist_service._to_watchlist_dict(item)

        assert result["unread_alerts"] == 1  # Only alert1 is unread

    def test_to_alert_dict(self, watchlist_service):
        """Test alert conversion to dict."""
        alert = MagicMock(spec=Alert)
        alert.id = 1
        alert.watchlist_item_id = 10
        alert.alert_type = "expiration"
        alert.priority = "high"
        alert.title = "Patent Expiring"
        alert.message = "Your patent is expiring soon"
        alert.related_patent_number = "US12345678"
        alert.related_data = {"foo": "bar"}
        alert.trigger_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        alert.due_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        alert.is_read = False
        alert.is_dismissed = False
        alert.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        result = watchlist_service._to_alert_dict(alert)

        assert result["id"] == 1
        assert result["alert_type"] == "expiration"
        assert result["priority"] == "high"
        assert result["is_read"] == False


class TestWatchlistRouteSchemas:
    """Test watchlist API schemas."""

    def test_add_request_schema(self):
        """Test WatchlistAddRequest schema."""
        from src.api.routes.watchlist import WatchlistAddRequest

        request = WatchlistAddRequest(
            item_type="patent",
            item_value="US12345678",
            name="My Patent",
        )

        assert request.item_type == "patent"
        assert request.item_value == "US12345678"
        assert request.notify_expiration == True

    def test_update_request_schema(self):
        """Test WatchlistUpdateRequest schema."""
        from src.api.routes.watchlist import WatchlistUpdateRequest

        request = WatchlistUpdateRequest(
            name="Updated Name",
            notify_expiration=False,
        )

        assert request.name == "Updated Name"
        assert request.notify_expiration == False

    def test_alert_summary_response(self):
        """Test AlertSummaryResponse schema."""
        from src.api.routes.watchlist import AlertSummaryResponse

        response = AlertSummaryResponse(
            total_unread=5,
            by_type={"expiration": 3, "maintenance_fee": 2},
            by_priority={"high": 2, "medium": 3},
            critical_count=0,
            high_count=2,
        )

        assert response.total_unread == 5
        assert response.critical_count == 0


class TestStatsService:
    """Tests for StatsService."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_empty(self):
        """Test dashboard stats with empty database."""
        from src.services.stats_service import StatsService

        service = StatsService()
        mock_session = AsyncMock()

        # Mock all the count queries to return 0
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = mock_result

        stats = await service.get_dashboard_stats(mock_session)

        assert stats["patents"]["total"] == 0
        assert stats["watchlist"]["count"] == 0

    @pytest.mark.asyncio
    async def test_get_system_status(self):
        """Test system status check."""
        from src.services.stats_service import StatsService

        service = StatsService()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0  # No patents

        mock_session.execute.return_value = mock_result

        status = await service.get_system_status(mock_session)

        assert status["api_server"] == "operational"
        assert status["database"] == "operational"  # Query succeeded
