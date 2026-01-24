from datetime import date, timedelta

from src.pipeline.expiration_calc import (
    calculate_expiration_date,
    calculate_maintenance_fee_dates,
    determine_patent_status,
    days_until_expiration,
)


def test_utility_patent_20_year_term():
    filing = date(2010, 6, 15)
    result = calculate_expiration_date(filing_date=filing, grant_date=date(2013, 3, 1))
    expected = filing + timedelta(days=20 * 365)
    assert result == expected


def test_design_patent_15_year_term():
    grant = date(2020, 1, 1)
    result = calculate_expiration_date(
        filing_date=date(2019, 1, 1),
        grant_date=grant,
        patent_type="design",
    )
    expected = grant + timedelta(days=15 * 365)
    assert result == expected


def test_pta_extends_term():
    filing = date(2010, 1, 1)
    base = calculate_expiration_date(filing_date=filing, grant_date=date(2013, 1, 1), pta_days=0)
    extended = calculate_expiration_date(filing_date=filing, grant_date=date(2013, 1, 1), pta_days=365)
    assert extended == base + timedelta(days=365)


def test_pte_extends_term():
    filing = date(2005, 1, 1)
    result = calculate_expiration_date(
        filing_date=filing,
        grant_date=date(2008, 1, 1),
        pte_days=1825,  # 5 years pharmaceutical extension
    )
    base = filing + timedelta(days=20 * 365)
    assert result == base + timedelta(days=1825)


def test_terminal_disclaimer_limits_term():
    filing = date(2010, 1, 1)
    disclaimer_date = date(2025, 6, 1)
    result = calculate_expiration_date(
        filing_date=filing,
        grant_date=date(2013, 1, 1),
        terminal_disclaimer_date=disclaimer_date,
    )
    assert result == disclaimer_date


def test_no_dates_returns_none():
    result = calculate_expiration_date(filing_date=None, grant_date=None)
    assert result is None


def test_maintenance_fee_schedule():
    grant = date(2020, 1, 1)
    fees = calculate_maintenance_fee_dates(grant)
    assert len(fees) == 3
    assert fees[0]["fee_year"] == 3
    assert fees[1]["fee_year"] == 7
    assert fees[2]["fee_year"] == 11
    # Check order
    assert fees[0]["due_date"] < fees[1]["due_date"] < fees[2]["due_date"]


def test_maintenance_fee_grace_period():
    grant = date(2020, 1, 1)
    fees = calculate_maintenance_fee_dates(grant)
    for fee in fees:
        assert fee["grace_period_end"] > fee["due_date"]


def test_status_active():
    future = date.today() + timedelta(days=365)
    status = determine_patent_status(expiration_date=future)
    assert status == "active"


def test_status_expired():
    past = date.today() - timedelta(days=1)
    status = determine_patent_status(expiration_date=past)
    assert status == "expired"


def test_status_unknown():
    status = determine_patent_status(expiration_date=None)
    assert status == "unknown"


def test_days_until_expiration():
    future = date.today() + timedelta(days=100)
    assert days_until_expiration(future) == 100


def test_days_until_expiration_none():
    assert days_until_expiration(None) is None


def test_days_until_expiration_negative():
    past = date.today() - timedelta(days=50)
    assert days_until_expiration(past) == -50
