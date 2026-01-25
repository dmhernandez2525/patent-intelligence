# Phase 9: White Space Discovery - Software Design Document

## Overview

Provides technology gap analysis and innovation opportunity discovery by analyzing CPC code coverage patterns across the patent database. Identifies under-patented technology areas, abandoned technology goldmines, cross-domain combination opportunities, and emerging gaps where filing activity has recently declined.

## Architecture

```
Frontend (WhiteSpacePage)
    |
    v
GET  /api/whitespace/coverage
GET  /api/whitespace/gaps
GET  /api/whitespace/opportunities
GET  /api/whitespace/sections/{section}
    |
    v
WhitespaceService
    |
    +-- get_coverage_analysis()         --> CPC section distribution & density
    +-- get_white_spaces()              --> Technology gaps by category
    +-- get_cross_domain_opportunities()--> Cross-section combination potential
    +-- get_section_overview()          --> Detailed section breakdown
    |
    v
Patent model (SQLAlchemy) - CPC codes, filing dates, status, citations
```

## Components

### 1. Whitespace Service (`src/services/whitespace_service.py`)

**CPC_SECTIONS Dictionary**
Maps all 9 CPC section prefixes to their full names:
- A: Human Necessities
- B: Performing Operations; Transporting
- C: Chemistry; Metallurgy
- D: Textiles; Paper
- E: Fixed Constructions
- F: Mechanical Engineering; Lighting; Heating; Weapons
- G: Physics
- H: Electricity
- Y: General Tagging of New Technological Developments

**get_coverage_analysis(session, min_patents)**
- Calculates per-section patent counts and percentages
- Identifies low-coverage sections (below 5% threshold)
- Computes density metrics (patents per CPC subclass)
- Returns sections ordered by total patent count

**get_white_spaces(session, section, min_gap_size, limit)**
- Identifies technology gaps using multiple heuristics:
  1. **Abandoned Goldmines**: CPC areas with 10+ patents but <2 active, high citations
  2. **Dormant Areas**: Previously active (5+ patents 3-5 years ago), no recent filings
  3. **Consolidation Opportunities**: Few assignees dominating a CPC area
  4. **Emerging Gaps**: Declining filing rates in the last 2 years
  5. **Minor Gaps**: Small CPC areas with limited coverage

**get_cross_domain_opportunities(session, section1, section2, limit)**
- Finds patents filed in multiple CPC sections
- Calculates combination rarity scores
- Identifies synergy potential based on filing patterns
- Returns opportunities sorted by rarity/impact

**get_section_overview(session, section)**
- Provides detailed breakdown of a CPC section
- Top CPC classes by patent count
- Active vs expired patent ratios
- Recent filing trends (3-year window)
- Top assignees in the section

### 2. API Endpoints (`src/api/routes/whitespace.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/whitespace/coverage` | GET | CPC section coverage analysis |
| `/api/whitespace/gaps` | GET | Technology gap opportunities |
| `/api/whitespace/opportunities` | GET | Cross-domain combination finder |
| `/api/whitespace/sections/{section}` | GET | Detailed section breakdown |

**Query Parameters:**
- `section`: Filter by CPC section (A-H, Y)
- `section1`, `section2`: Cross-domain comparison sections
- `min_gap_size`: Minimum patent count for gap detection (default: 5)
- `limit`: Maximum results to return (default: 20)

### 3. Pydantic Schemas (`src/api/schemas/whitespace.py`)

```python
class SectionCoverage:
    section: str
    section_name: str
    patent_count: int
    percentage: float
    density: float
    is_low_coverage: bool

class WhiteSpace:
    cpc_code: str
    cpc_name: str
    opportunity_type: str  # abandoned_goldmine, dormant, etc.
    total_patents: int
    active_patents: int
    avg_citations: float
    top_assignees: list[str]
    score: float
    rationale: str

class CrossDomainOpportunity:
    section1: str
    section2: str
    overlap_patents: int
    example_cpcs: list[str]
    rarity_score: float
    synergy_potential: str
```

### 4. Frontend (`frontend/src/pages/WhiteSpacePage.tsx`)

**Three Main Panels:**

1. **Section Overview Grid**
   - 9 CPC section cards with patent counts
   - Visual indicators for low-coverage sections
   - Click to drill down into section details

2. **White Space Explorer**
   - Filterable list of technology gaps
   - Opportunity type badges (color-coded)
   - Score indicators and rationale display
   - Top assignees chips

3. **Cross-Domain Opportunities**
   - Section pair selector
   - Rarity score visualization
   - Example patent chips
   - Synergy potential descriptions

## Design Decisions

1. **CPC-based granularity**: Using 4-character CPC prefixes (e.g., "H01L") provides meaningful technology groupings while remaining computationally tractable across millions of patents.

2. **Multiple gap heuristics**: Different types of white space require different detection strategies - abandoned high-citation patents represent different opportunities than simply under-patented areas.

3. **Citation-weighted scoring**: Incorporating citation counts distinguishes valuable technology gaps from simply obscure areas with no commercial interest.

4. **Section-level entry point**: Starting analysis at CPC section level (A-H, Y) provides intuitive navigation before drilling into specific technology areas.

5. **Assignee concentration analysis**: Identifying CPC areas dominated by few assignees reveals consolidation opportunities and potential licensing targets.

6. **Time-windowed trends**: Using 2-3 year windows for "recent" activity balances responsiveness to market changes against noise from annual variations.

7. **Pre-computed density metrics**: Calculating patents-per-subclass density normalizes comparisons across sections with varying CPC hierarchy depths.

## Database Queries

Key query patterns used:

```sql
-- Section coverage
SELECT SUBSTR(UNNEST(cpc_codes), 1, 1) as section,
       COUNT(DISTINCT id) as count
FROM patents
WHERE cpc_codes IS NOT NULL
GROUP BY section;

-- Abandoned goldmines
SELECT SUBSTR(UNNEST(cpc_codes), 1, 4) as cpc,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
       AVG(citation_count) as citations
FROM patents
GROUP BY cpc
HAVING COUNT(*) >= 10 AND active < 2 AND citations > 5;

-- Cross-domain patents
SELECT cpc_codes
FROM patents
WHERE cpc_codes && ARRAY['H%'] AND cpc_codes && ARRAY['G%'];
```

## Performance Considerations

- CPC substring operations use PostgreSQL's native string functions
- Results are limited by default to prevent full-table scans
- Coverage analysis can be cached at application level (changes infrequently)
- Indexes on `cpc_codes` (GIN), `filing_date`, and `status` support query patterns
