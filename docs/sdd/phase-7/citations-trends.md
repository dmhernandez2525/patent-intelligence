# Phase 7: Citation Network & Trend Analysis - Software Design Document

## Overview

Provides citation network graph traversal, technology trend analysis, and competitive landscape insights. Enables visualizing patent citation relationships, identifying technology growth areas, and analyzing filing patterns across CPC codes, countries, and assignees.

## Architecture

```
Frontend (TrendsPage)
    |
    v
GET /api/analysis/trends
GET /api/analysis/citations/{patent_number}
GET /api/analysis/citations/{patent_number}/stats
    |
    v
CitationService
    |
    +-- get_citation_network()    --> BFS graph traversal
    +-- get_technology_trends()   --> Yearly counts, CPC trends, growth leaders
    +-- get_citation_stats()      --> Forward/backward counts, citation index
    |
    v
Patent model + Citation model (SQLAlchemy)
```

## Components

### 1. Citation Service (`src/services/citation_service.py`)

**get_citation_network(patent_number, depth, max_nodes)**
- BFS traversal starting from target patent
- Follows both forward citations (patents cited by target) and backward citations (patents citing target)
- Returns nodes (patent metadata) and edges (citation relationships)
- Respects max_nodes limit to prevent unbounded graph growth
- Each node includes depth level for layered visualization

**get_technology_trends(cpc_prefix, country, years, top_n)**
- Aggregates patent filing counts by year
- Identifies top CPC technology areas by volume
- Calculates growth rates by comparing recent vs earlier filing periods
- Ranks top patent-filing organizations
- Supports filtering by CPC prefix and country

**get_citation_stats(patent_number)**
- Counts forward citations (patents this one cites)
- Counts backward citations (patents that cite this one)
- Computes average citations for same year/CPC cohort
- Derives citation index (backward_count / field_average) as impact metric

### 2. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analysis/trends` | GET | Technology trend analysis |
| `/api/analysis/citations/{number}` | GET | Citation network graph |
| `/api/analysis/citations/{number}/stats` | GET | Citation statistics |

### 3. Frontend (`frontend/src/pages/TrendsPage.tsx`)

Two view modes:

**Technology Trends**
- Configurable filters: CPC prefix, country, time range
- Bar chart of yearly patent filing counts
- Three-column grid: Top CPC areas, Growth leaders (with directional arrows), Top assignees
- Auto-fetches on filter change via TanStack Query

**Citation Network**
- Patent number input with depth/max_nodes configuration
- Citation stats summary (forward, backward, field avg, citation index)
- Nodes grouped by depth level with patent cards
- Edge list showing citation relationships with type badges

## Design Decisions

1. **BFS with max_nodes cap**: Prevents exponential graph explosion while ensuring breadth-first coverage of the most directly relevant citations.

2. **Growth rate via period splitting**: Divides the time range at midpoint, comparing recent vs earlier halves. Minimum threshold of 5 earlier filings prevents noise from low-volume codes.

3. **Citation index as impact metric**: Ratio of backward citations to field average provides normalized comparison across technology areas with different baseline citation rates.

4. **CPC code truncation to 4 chars**: Groups related sub-classifications (e.g., H01L21/00, H01L29/00) into broader technology areas for trend visibility.

5. **Separate forward/backward queries**: Uses outerjoin for forward (cited patent may not be in DB) vs inner join for backward (citing patent must exist), ensuring correct data regardless of database completeness.

6. **Frontend depth grouping**: Displays network nodes grouped by BFS depth level rather than a force-directed graph, providing clear hierarchical visualization without a graph library dependency.
