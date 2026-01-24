import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.ingesters.epo_ingester import EPOIngester
from src.ingesters.epo_client import EPOClient, EPOAuthError, EPOAPIError


class TestEPOClient:
    """Test EPO API client."""

    def test_init_defaults(self):
        client = EPOClient(consumer_key="test_key", consumer_secret="test_secret")
        assert client.consumer_key == "test_key"
        assert client.consumer_secret == "test_secret"
        assert client._access_token is None

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self):
        client = EPOClient(consumer_key="", consumer_secret="")
        with pytest.raises(EPOAuthError, match="consumer_key and consumer_secret are required"):
            await client._authenticate()

    def test_api_error(self):
        err = EPOAPIError(403, "Rate limited")
        assert err.status_code == 403
        assert "403" in str(err)
        assert "Rate limited" in str(err)


class TestEPOIngester:
    """Test EPO ingester parsing logic."""

    def test_source_name(self):
        ingester = EPOIngester(consumer_key="key", consumer_secret="secret")
        assert ingester.source_name == "epo"

    def test_build_search_query_default(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        query = ingester._build_search_query(since=None)
        assert "pd>=2020" in query
        assert "pn=EP" in query

    def test_build_search_query_with_since(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        since = datetime(2023, 6, 15)
        query = ingester._build_search_query(since=since)
        assert "pd>=20230615" in query

    def test_get_total_count(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        result = {
            "ops:world-patent-data": {
                "ops:biblio-search": {
                    "@total-result-count": "1500"
                }
            }
        }
        assert ingester._get_total_count(result) == 1500

    def test_get_total_count_missing(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        assert ingester._get_total_count({}) is None

    def test_extract_title_english(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        biblio = {
            "invention-title": [
                {"@lang": "de", "$": "German Title"},
                {"@lang": "en", "$": "English Title"},
            ]
        }
        assert ingester._extract_title(biblio) == "English Title"

    def test_extract_title_fallback(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        biblio = {
            "invention-title": [{"@lang": "fr", "$": "French Title"}]
        }
        assert ingester._extract_title(biblio) == "French Title"

    def test_extract_title_empty(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        assert ingester._extract_title({}) is None

    def test_extract_applicants(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        biblio = {
            "parties": {
                "applicants": {
                    "applicant": [
                        {
                            "@data-format": "epodoc",
                            "applicant-name": {
                                "name": {"$": "SIEMENS AG"}
                            },
                        }
                    ]
                }
            }
        }
        name, org = ingester._extract_applicants(biblio)
        assert name == "SIEMENS AG"
        assert org == "SIEMENS AG"

    def test_extract_inventors(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        biblio = {
            "parties": {
                "inventors": {
                    "inventor": [
                        {
                            "@data-format": "epodoc",
                            "inventor-name": {"name": {"$": "SMITH John"}},
                        },
                        {
                            "@data-format": "epodoc",
                            "inventor-name": {"name": {"$": "JONES Alice"}},
                        },
                    ]
                }
            }
        }
        inventors = ingester._extract_inventors(biblio)
        assert inventors == ["SMITH John", "JONES Alice"]

    def test_extract_text_content_string(self):
        assert EPOIngester._extract_text_content({"p": "Hello"}) == "Hello"

    def test_extract_text_content_list(self):
        result = EPOIngester._extract_text_content({"p": [{"$": "Para 1"}, {"$": "Para 2"}]})
        assert result == "Para 1 Para 2"

    def test_extract_text_content_dict(self):
        result = EPOIngester._extract_text_content({"p": {"$": "Single paragraph"}})
        assert result == "Single paragraph"

    def test_parse_exchange_document(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        doc = {
            "@country": "EP",
            "@doc-number": "1234567",
            "@kind": "A1",
            "bibliographic-data": {
                "invention-title": [{"@lang": "en", "$": "A Novel Battery"}],
                "parties": {
                    "applicants": {
                        "applicant": [{
                            "@data-format": "epodoc",
                            "applicant-name": {"name": {"$": "TESLA INC"}},
                        }]
                    },
                    "inventors": {
                        "inventor": [{
                            "@data-format": "epodoc",
                            "inventor-name": {"name": {"$": "MUSK Elon"}},
                        }]
                    },
                },
                "patent-classifications": {
                    "patent-classification": []
                },
            },
        }
        result = ingester._parse_exchange_document(doc)
        assert result is not None
        assert result.patent_number == "EP1234567A1"
        assert result.title == "A Novel Battery"
        assert result.assignee_organization == "TESLA INC"
        assert result.inventors == ["MUSK Elon"]
        assert result.country == "EP"

    def test_parse_exchange_document_no_number(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        doc = {"@country": "EP", "@doc-number": "", "@kind": "A1"}
        result = ingester._parse_exchange_document(doc)
        assert result is None

    def test_parse_family_members(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        result = {
            "ops:world-patent-data": {
                "ops:patent-family": {
                    "ops:family-member": [
                        {
                            "publication-reference": {
                                "document-id": [{
                                    "country": {"$": "US"},
                                    "doc-number": {"$": "9876543"},
                                    "kind": {"$": "B2"},
                                }]
                            }
                        },
                        {
                            "publication-reference": {
                                "document-id": [{
                                    "country": {"$": "JP"},
                                    "doc-number": {"$": "2020123456"},
                                    "kind": {"$": "A"},
                                }]
                            }
                        },
                    ]
                }
            }
        }
        members = ingester._parse_family_members(result)
        assert len(members) == 2
        assert members[0]["patent_number"] == "US9876543B2"
        assert members[0]["country"] == "US"
        assert members[1]["country"] == "JP"

    def test_parse_legal_events_empty(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        assert ingester._parse_legal_events({}) == []

    def test_parse_search_results_empty(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        assert ingester._parse_search_results({}) == []

    def test_extract_date(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        biblio = {
            "application-reference": {
                "document-id": [
                    {"date": {"$": "20200315"}}
                ]
            }
        }
        assert ingester._extract_date(biblio, "application-reference") == "2020-03-15"

    def test_extract_date_missing(self):
        ingester = EPOIngester(consumer_key="k", consumer_secret="s")
        assert ingester._extract_date({}, "application-reference") is None
