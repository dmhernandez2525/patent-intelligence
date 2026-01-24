# Phase 3: Patent Search Engine - Software Design Document

## Overview

The Patent Search Engine provides three search modalities for querying the patent database: full-text search using PostgreSQL trigram similarity, semantic search using PatentSBERTa embeddings with pgvector, and hybrid search combining both via Reciprocal Rank Fusion (RRF).

## Architecture

```
Frontend (SearchPage)
    |
    v
POST /api/search
    |
    v
SearchRequest (Pydantic validation)
    |
    v
PatentSearchService
    |
    +-- fulltext_search()  --> PostgreSQL ILIKE + trigram similarity
    +-- semantic_search()  --> PatentSBERTa embedding + pgvector cosine distance
    +-- hybrid_search()   --> RRF fusion of both approaches
    |
    v
SearchResponse (paginated results with relevance scores)
```

## Components

### 1. Search Service (`src/ai/search_service.py`)

#### PatentSearchService

Singleton service providing three search methods:

**Full-text Search:**
- Uses PostgreSQL `ILIKE` for broad matching across title, abstract, patent number, assignee
- Ranks results using `pg_trgm` similarity function
- Computes `greatest(similarity(title, query), similarity(abstract, query))` for relevance

**Semantic Search:**
- Generates query embedding using PatentSBERTa (768-dim vectors)
- Uses pgvector `cosine_distance` operator for nearest-neighbor search
- Filters to patents that have computed embeddings
- Relevance score = `1 - cosine_distance`

**Hybrid Search (Default):**
- Fetches top `3 * per_page` results from both full-text and semantic
- Applies Reciprocal Rank Fusion with configurable semantic weight (default 0.6)
- RRF score: `sum(weight / (k + rank + 1))` with k=60
- Falls back to full-text if no embeddings are available

#### Filter Application

All search methods support identical filters via `_apply_filters()`:
- `country` - Exact match on country code
- `status` - Exact match on patent status
- `assignee` - ILIKE partial match on assignee organization
- `cpc_codes` - PostgreSQL array overlap check
- `date_from` / `date_to` - Filing date range

### 2. API Schema (`src/api/schemas/search.py`)

**SearchRequest:**
- `query` (str, 1-1000 chars, required)
- `search_type` (fulltext|semantic|hybrid, default: hybrid)
- `cpc_codes` (list[str], optional)
- `country`, `status`, `assignee` (str, optional)
- `date_from`, `date_to` (date, optional)
- `page` (int, >=1), `per_page` (int, 1-100)

**SearchResultItem:**
- Patent metadata: number, title, abstract, dates, assignee, inventors, CPCs
- `status`, `country`, `citation_count`
- `relevance_score` (float, 0-1 for fulltext/semantic, normalized for hybrid)

**SearchResponse:**
- `results` (list[SearchResultItem])
- `total`, `query`, `search_type`, `page`, `per_page`

### 3. API Route (`src/api/routes/search.py`)

Single endpoint: `POST /api/search`
- Validates request via Pydantic
- Builds filter dict from optional parameters
- Dispatches to appropriate search method
- Returns SearchResponse with serialized results

### 4. Frontend (`frontend/src/pages/SearchPage.tsx`)

- Search bar with query input
- Search mode selector (Hybrid/Semantic/Fulltext)
- Filter panel: country, status, CPC code, assignee
- Results list with patent cards showing:
  - Patent number with colored status badge
  - Title and abstract (line-clamped)
  - Assignee, filing date, CPC codes
  - Relevance score percentage
- Pagination controls

## Design Decisions

1. **ILIKE + trigram over ts_vector**: PatentsView data lacks pre-computed tsvector; trigram similarity provides good ranking without requiring full-text index rebuilds.

2. **Lazy embedding service initialization**: The embedding model is loaded on first use to avoid blocking API startup.

3. **RRF over linear combination**: RRF is rank-based rather than score-based, making it robust to score distribution differences between search methods.

4. **3x fusion window**: Fetching 3x results for fusion ensures good coverage while keeping memory usage bounded.

5. **Cosine distance (not inner product)**: Normalized embeddings make cosine distance equivalent to angular distance, providing better semantic similarity for variable-length patent text.

## Performance Considerations

- Full-text: O(n) scan with ILIKE; can be improved with GIN trigram index
- Semantic: pgvector uses IVFFlat/HNSW index for approximate nearest neighbors
- Hybrid: 2x the cost of individual methods but cached in application memory during fusion
- Pagination limits prevent excessive memory usage for large result sets

## Testing

Tests in `tests/unit/test_search_service.py`:
- `_patent_to_result` conversion (dates, None handling, score rounding)
- `_apply_filters` (all filter types, combinations)
- Hybrid RRF logic (fallback to fulltext, score combination)
- Schema validation (request validation, response structure)
