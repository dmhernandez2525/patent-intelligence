from src.pipeline.normalizer import normalize_patent_number, normalize_cpc_code, parse_date


def test_normalize_patent_number_adds_us_prefix():
    assert normalize_patent_number("12345678", "US") == "US12345678"


def test_normalize_patent_number_preserves_existing_prefix():
    assert normalize_patent_number("US12345678", "US") == "US12345678"


def test_normalize_patent_number_strips_spaces():
    assert normalize_patent_number("US 12,345,678", "US") == "US12345678"


def test_normalize_cpc_code():
    assert normalize_cpc_code("  h01l 21/00  ") == "H01L21/00"


def test_parse_date_iso_format():
    result = parse_date("2024-01-15")
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_date_none():
    assert parse_date(None) is None


def test_parse_date_invalid():
    assert parse_date("not-a-date") is None
