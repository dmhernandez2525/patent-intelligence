import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from src.services.expiration_service import ExpirationService


@pytest.fixture
def service():
    return ExpirationService()


class TestToExpirationItem:
    """Test the _to_expiration_item method."""

    def _make_patent(self, **overrides):
        patent = MagicMock()
        patent.patent_number = overrides.get("patent_number", "US-12345-A1")
        patent.title = overrides.get("title", "Test Patent")
        patent.abstract = overrides.get("abstract", "An abstract")
        patent.expiration_date = overrides.get("expiration_date", date.today() + timedelta(days=45))
        patent.filing_date = overrides.get("filing_date", date(2005, 3, 15))
        patent.grant_date = overrides.get("grant_date", date(2007, 6, 1))
        patent.assignee_organization = overrides.get("assignee_organization", "Acme Corp")
        patent.cpc_codes = overrides.get("cpc_codes", ["H01L21/00"])
        patent.country = overrides.get("country", "US")
        patent.status = overrides.get("status", "active")
        patent.citation_count = overrides.get("citation_count", 12)
        patent.patent_type = overrides.get("patent_type", "utility")
        patent.maintenance_fees = overrides.get("maintenance_fees", [])
        return patent

    def _make_fee(self, status="pending", due_date=None, amount=None):
        fee = MagicMock()
        fee.status = status
        fee.due_date = due_date or (date.today() + timedelta(days=60))
        fee.amount_usd = amount
        fee.grace_period_end = fee.due_date + timedelta(days=180)
        return fee

    def test_basic_conversion(self, service: ExpirationService):
        today = date.today()
        patent = self._make_patent(expiration_date=today + timedelta(days=30))
        result = service._to_expiration_item(patent, today)

        assert result["patent_number"] == "US-12345-A1"
        assert result["title"] == "Test Patent"
        assert result["days_until_expiration"] == 30
        assert result["status"] == "active"
        assert result["country"] == "US"

    def test_fee_status_no_fees(self, service: ExpirationService):
        today = date.today()
        patent = self._make_patent(maintenance_fees=[])
        result = service._to_expiration_item(patent, today)
        assert result["maintenance_fee_status"] == "no_fees"

    def test_fee_status_overdue(self, service: ExpirationService):
        today = date.today()
        overdue_fee = self._make_fee(status="pending", due_date=today - timedelta(days=10))
        patent = self._make_patent(maintenance_fees=[overdue_fee])
        result = service._to_expiration_item(patent, today)
        assert result["maintenance_fee_status"] == "overdue"

    def test_fee_status_due_soon(self, service: ExpirationService):
        today = date.today()
        soon_fee = self._make_fee(status="pending", due_date=today + timedelta(days=30))
        patent = self._make_patent(maintenance_fees=[soon_fee])
        result = service._to_expiration_item(patent, today)
        assert result["maintenance_fee_status"] == "due_soon"

    def test_fee_status_current(self, service: ExpirationService):
        today = date.today()
        future_fee = self._make_fee(status="pending", due_date=today + timedelta(days=200))
        patent = self._make_patent(maintenance_fees=[future_fee])
        result = service._to_expiration_item(patent, today)
        assert result["maintenance_fee_status"] == "current"

    def test_fee_status_all_paid(self, service: ExpirationService):
        today = date.today()
        paid_fee = self._make_fee(status="paid", due_date=today - timedelta(days=100))
        patent = self._make_patent(maintenance_fees=[paid_fee])
        result = service._to_expiration_item(patent, today)
        assert result["maintenance_fee_status"] == "all_paid"

    def test_next_fee_info(self, service: ExpirationService):
        today = date.today()
        next_due = today + timedelta(days=45)
        fee = self._make_fee(status="pending", due_date=next_due, amount=1600.0)
        patent = self._make_patent(maintenance_fees=[fee])
        result = service._to_expiration_item(patent, today)
        assert result["next_fee_date"] == next_due.isoformat()
        assert result["next_fee_amount"] == 1600.0

    def test_none_expiration_date(self, service: ExpirationService):
        today = date.today()
        patent = self._make_patent(expiration_date=None)
        result = service._to_expiration_item(patent, today)
        assert result["days_until_expiration"] == 0
        assert result["expiration_date"] is None

    def test_none_optional_fields(self, service: ExpirationService):
        today = date.today()
        patent = self._make_patent(
            abstract=None,
            filing_date=None,
            grant_date=None,
            assignee_organization=None,
            cpc_codes=None,
            citation_count=None,
            patent_type=None,
        )
        result = service._to_expiration_item(patent, today)
        assert result["abstract"] is None
        assert result["filing_date"] is None
        assert result["assignee_organization"] is None

    def test_expired_patent_negative_days(self, service: ExpirationService):
        today = date.today()
        patent = self._make_patent(
            expiration_date=today - timedelta(days=10),
            status="expired",
        )
        result = service._to_expiration_item(patent, today)
        assert result["days_until_expiration"] == -10


class TestExpirationSchemas:
    """Test the expiration schemas."""

    def test_expiring_patent_item(self):
        from src.api.schemas.expiration import ExpiringPatentItem

        item = ExpiringPatentItem(
            patent_number="US-123",
            title="Test",
            country="US",
            status="active",
            days_until_expiration=30,
            maintenance_fee_status="current",
        )
        assert item.patent_number == "US-123"
        assert item.days_until_expiration == 30

    def test_maintenance_fee_item(self):
        from src.api.schemas.expiration import MaintenanceFeeItem

        item = MaintenanceFeeItem(
            patent_number="US-123",
            title="Test",
            fee_year=4,
            due_date="2025-06-15",
            days_until_due=45,
            status="pending",
            amount_usd=1600.0,
        )
        assert item.fee_year == 4
        assert item.amount_usd == 1600.0

    def test_stats_response(self):
        from src.api.schemas.expiration import ExpirationStatsResponse

        stats = ExpirationStatsResponse(
            expiring_30_days=10,
            expiring_90_days=50,
            expiring_180_days=120,
            expiring_365_days=300,
            recently_lapsed=25,
            pending_maintenance_fees=80,
            top_sectors=[{"cpc_code": "H01L", "count": 15}],
            monthly_timeline=[{"month": "2025-02-01", "count": 8}],
        )
        assert stats.expiring_30_days == 10
        assert len(stats.top_sectors) == 1
        assert stats.top_sectors[0].cpc_code == "H01L"

    def test_dashboard_response(self):
        from src.api.schemas.expiration import (
            ExpirationDashboardResponse,
            ExpirationStatsResponse,
        )

        resp = ExpirationDashboardResponse(
            stats=ExpirationStatsResponse(
                expiring_30_days=0,
                expiring_90_days=0,
                expiring_180_days=0,
                expiring_365_days=0,
                recently_lapsed=0,
                pending_maintenance_fees=0,
                top_sectors=[],
                monthly_timeline=[],
            ),
            expiring_soon=[],
            recently_lapsed=[],
            upcoming_fees=[],
        )
        assert resp.stats.expiring_30_days == 0
