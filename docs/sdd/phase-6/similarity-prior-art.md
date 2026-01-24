# Phase 6: Patent Similarity & Prior Art - Software Design Document

## Overview

Provides patent similarity search and prior art discovery using PatentSBERTa embeddings and citation network analysis. Enables finding semantically similar patents, identifying potential prior art, and understanding the patent landscape around a technology.

## Architecture

```
Frontend (SimilarityPage)
    |
    v
POST /api/similarity/{similar|prior-art}
GET  /api/similarity/landscape/{patent_number}
    |
    v
SimilarityService
    |
    +-- find_similar_patents()   --> Cosine similarity on embeddings
    +-- find_prior_art()         --> Semantic + citation analysis
    +-- get_patent_landscape()   --> Full competitive context
    |
    v
Patent model + pgvector + Citation table
```

## Components

### 1. Similarity Service (`src/services/similarity_service.py`)

**find_similar_patents(patent_number|text_query, top_k, min_score, filters)**
- Generates or retrieves query embedding
- Computes cosine similarity against all embedded patents
- Supports filtering by country, CPC code, exclude-same-assignee
- Returns top-K results above min_score threshold

**find_prior_art(patent_number|text_query, filing_date_before, top_k, min_score)**
- Combines two approaches:
  1. Semantic: Similar patents filed before the target's filing date
  2. Citations: Patents cited by the target (known prior art)
- Merges results with deduplication, boosts patents found in both
- Returns categorized results with source attribution

**get_patent_landscape(patent_number, radius)**
- Similar patents (semantic neighbors)
- Cited patents (what the patent references)
- Citing patents (who references this patent)
- Competitors (other assignees in same CPC space)

### 2. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/similarity/similar` | POST | Find similar patents |
| `/api/similarity/prior-art` | POST | Prior art discovery |
| `/api/similarity/landscape/{number}` | GET | Patent landscape |

### 3. Frontend (`frontend/src/pages/SimilarityPage.tsx`)

- Mode selector: Similar Patents / Prior Art
- Input type toggle: Text concept / Patent number
- Configurable: top_k, min_score, exclude_same_assignee
- Results with color-coded similarity scores (red=high, green=low risk)
- Prior art stats (semantic vs citation source breakdown)

## Design Decisions

1. **Embedding-first with citation fallback**: Semantic similarity catches conceptual overlap that keyword search misses; citations provide ground truth prior art.

2. **Source attribution**: Results labeled "semantic", "citation", or "both" to indicate discovery method and confidence level.

3. **Post-filtering for assignee exclusion**: Fetches 2x results then filters, avoiding index-level complexity.

4. **Separate min_score defaults**: Similar (0.5) vs Prior Art (0.4) - prior art uses lower threshold since older patents may use different terminology.

5. **Landscape endpoint**: Provides full context in one call for patent analysis dashboards.
