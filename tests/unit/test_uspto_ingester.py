import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.ingesters.uspto_ingester import USPTOIngester


@pytest.fixture
def ingester():
    return USPTOIngester()


def test_ingester_source_name(ingester: USPTOIngester):
    assert ingester.source_name == "uspto"


def test_build_query_default(ingester: USPTOIngester):
    query = ingester._build_query(since=None)
    assert "_gte" in query
    assert "patent_date" in query["_gte"]


def test_build_query_with_since(ingester: USPTOIngester):
    from datetime import datetime
    since = datetime(2024, 6, 1)
    query = ingester._build_query(since=since)
    assert query == {"_gte": {"patent_date": "2024-06-01"}}


def test_parse_patent_basic(ingester: USPTOIngester):
    raw = {
        "patent_id": "12345678",
        "patent_title": "Test Patent Title",
        "patent_abstract": "Test abstract",
        "patent_date": "2024-01-15",
        "patent_type": "utility",
        "patent_kind": "B2",
        "patent_num_claims": 10,
        "application": {
            "application_number": "16/123456",
            "filing_date": "2021-06-01",
        },
        "assignees": [
            {"assignee_organization": "Test Corp", "assignee_country": "US"}
        ],
        "inventors": [
            {"inventor_name_first": "John", "inventor_name_last": "Doe", "inventor_country": "US"},
            {"inventor_name_first": "Jane", "inventor_name_last": "Smith", "inventor_country": "US"},
        ],
        "cpcs": [
            {"cpc_group_id": "H01L21/00", "cpc_subclass_id": "H01L"},
            {"cpc_group_id": "H01L29/00", "cpc_subclass_id": "H01L"},
        ],
        "cited_patents": [
            {"cited_patent_id": "11111111", "cited_patent_category": "cited by examiner"},
        ],
    }

    result = ingester._parse_patent(raw)

    assert result.patent_number == "12345678"
    assert result.title == "Test Patent Title"
    assert result.abstract == "Test abstract"
    assert result.grant_date == "2024-01-15"
    assert result.filing_date == "2021-06-01"
    assert result.assignee_organization == "Test Corp"
    assert result.inventors == ["John Doe", "Jane Smith"]
    assert "H01L21/00" in result.cpc_codes
    assert "H01L29/00" in result.cpc_codes
    assert result.country == "US"
    assert result.kind_code == "B2"
    assert len(result.citations) == 1


def test_parse_patent_individual_assignee(ingester: USPTOIngester):
    raw = {
        "patent_id": "99999999",
        "patent_title": "Individual Patent",
        "assignees": [
            {
                "assignee_organization": None,
                "assignee_individual_name_first": "Bob",
                "assignee_individual_name_last": "Builder",
            }
        ],
        "inventors": [],
        "cpcs": [],
        "cited_patents": [],
        "application": {},
    }

    result = ingester._parse_patent(raw)
    assert result.assignee == "Bob Builder"
    assert result.assignee_organization is None


def test_parse_patent_no_optional_fields(ingester: USPTOIngester):
    raw = {
        "patent_id": "55555555",
        "patent_title": "Minimal Patent",
        "assignees": None,
        "inventors": None,
        "cpcs": None,
        "cited_patents": None,
        "application": None,
    }

    result = ingester._parse_patent(raw)
    assert result.patent_number == "55555555"
    assert result.title == "Minimal Patent"
    assert result.inventors is None
    assert result.cpc_codes is None
    assert result.citations is None


def test_patent_fields_constant(ingester: USPTOIngester):
    assert "patent_id" in ingester.PATENT_FIELDS
    assert "patent_title" in ingester.PATENT_FIELDS
    assert "patent_abstract" in ingester.PATENT_FIELDS
