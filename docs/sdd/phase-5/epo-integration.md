# Phase 5: EPO International Data Integration - Software Design Document

## Overview

Integrates European Patent Office (EPO) Open Patent Services (OPS) as a second data source, enabling access to 90+ countries' patent data via DOCDB (bibliographic), INPADOC (legal status), and patent family databases.

## Architecture

```
IngestionPage (Frontend)
    |
    v (source: "epo")
POST /api/ingestion/trigger
    |
    v
Celery Task (orchestrator)
    |
    v
EPOIngester
    |
    v
EPOClient (OAuth2)
    |
    +-- search_publications()     --> CQL search API
    +-- get_published_data()      --> DOCDB bibliographic/abstract/claims
    +-- get_family()              --> INPADOC patent families
    +-- get_legal_status()        --> INPADOC legal events
    +-- get_register_data()       --> EP register (procedural)
    |
    v
patent_store.store_patent_batch() --> PostgreSQL
```

## Components

### 1. EPO API Client (`src/ingesters/epo_client.py`)

Handles all EPO OPS API communication:

**Authentication:**
- OAuth2 client credentials flow
- Base64-encoded consumer_key:consumer_secret
- Auto-refreshes token 60s before expiry
- Retry on 401 with fresh token

**Rate Limiting:**
- TokenBucketRateLimiter: 2 req/sec, burst of 10
- EPO free tier: 4GB/week bandwidth, 2.5 req/sec

**Methods:**
- `search_publications(query, range)` - CQL search with pagination
- `get_published_data(ref_type, format, number, endpoint)` - Bibliographic data
- `get_family(ref_type, format, number)` - INPADOC family members
- `get_legal_status(ref_type, format, number)` - Legal status events
- `get_register_data(format, number)` - EP register data

**Error Handling:**
- `EPOAuthError` for authentication failures
- `EPOAPIError` with status codes for API errors
- 404 returns None (not found, not error)
- 403 raises with rate-limit message

### 2. EPO Ingester (`src/ingesters/epo_ingester.py`)

Implements `BaseIngester` interface for EPO data:

**fetch_patents(offset, limit, since):**
- Builds CQL query for recent publications in EP/WO/GB/DE/FR
- Paginates using EPO range parameters (25 per batch)
- Yields `list[RawPatentData]` for each batch
- Stops when total_count exceeded or no more results

**fetch_patent_detail(patent_number):**
- Fetches full-cycle data (biblio + abstract + claims + description)
- Parses into complete RawPatentData

**fetch_legal_status(patent_number):**
- Returns list of legal events (grant, lapse, expiry, etc.)
- Useful for determining actual patent status

**fetch_family_members(patent_number):**
- Returns list of family member patent numbers and countries
- Enables patent family resolution

**Parsing Methods:**
- `_parse_exchange_document()` - Core parser for EPO exchange-document format
- `_extract_title()` - Prefers English, falls back to first available
- `_extract_abstract()` - Multi-paragraph text extraction
- `_extract_applicants()` - From parties/applicants (epodoc format)
- `_extract_inventors()` - From parties/inventors (epodoc format)
- `_extract_classifications()` - CPC and IPC codes from structured data
- `_extract_date()` - YYYYMMDD to YYYY-MM-DD conversion
- `_parse_family_members()` - Family member extraction
- `_parse_legal_events()` - Legal event extraction

### 3. Configuration

Settings in `src/config.py`:
- `epo_consumer_key` - EPO developer portal consumer key
- `epo_consumer_secret` - EPO developer portal consumer secret
- `epo_base_url` - OPS API base URL

### 4. Pipeline Integration

The Celery orchestrator (`src/pipeline/orchestrator.py`) now supports:
```python
if source == "epo":
    from src.ingesters.epo_ingester import EPOIngester
    ingester = EPOIngester()
```

### 5. Frontend Updates

IngestionPage now includes:
- Source selector dropdown (USPTO / EPO)
- Status queries scoped to selected source
- Updated description text

## EPO OPS API Notes

### CQL Query Syntax
```
pd>=2020 AND (pn=EP OR pn=WO OR pn=GB OR pn=DE OR pn=FR)
ti=battery AND pa=samsung
ic=H01L
```

### Data Formats
- **DOCDB**: country + number + kind (e.g., EP1234567A1)
- **EPODOC**: simplified format (e.g., EP1234567)
- **Original**: office-specific format

### Rate Limits (Registered Users)
- 2.5 requests/second sustained
- 4GB/week data transfer
- Max 100 results per search request
- Max 2000 results per query

### Key Patent Offices Covered
- EP (European Patent Office)
- WO (PCT/WIPO)
- GB, DE, FR, IT, ES, NL (national offices)
- JP, KR, CN (via DOCDB)
- US (mirrored from USPTO)

## Design Decisions

1. **OAuth2 with auto-refresh**: Token is refreshed 60s before expiry to avoid mid-request failures.

2. **25 results per batch**: Conservative to stay within rate limits; EPO max is 100 but throttles aggressively.

3. **CQL over REST search**: CQL provides richer query expressiveness for date ranges and office filtering.

4. **Separate client/ingester**: EPOClient handles auth/HTTP; EPOIngester handles parsing/normalization. Enables reuse of client for family/legal queries.

5. **epodoc format for parties**: Provides normalized names without address noise.

## Testing

Tests in `tests/unit/test_epo_ingester.py`:
- Client initialization and auth error handling
- Search query building with/without since date
- Exchange document parsing (full document, title extraction, applicants, inventors)
- Family member parsing
- Date extraction and edge cases
- Text content extraction helpers
