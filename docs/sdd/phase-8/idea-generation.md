# Phase 8: AI-Powered Idea Generation - Software Design Document

## Overview

Provides LLM-powered invention idea generation by analyzing expiring patents, technology trends, and cross-domain combinations. Uses Anthropic Claude or OpenAI as the generation backend with a structured fallback for environments without API keys.

## Architecture

```
Frontend (IdeasPage)
    |
    v
POST /api/ideas/generate
GET  /api/ideas/seeds
    |
    v
IdeaGenerationService
    |
    +-- generate_ideas()     --> Gather seeds + LLM call
    +-- get_seeds()          --> Preview available context
    |
    +-- _gather_seeds()      --> Query expiring/trending/high-impact patents
    +-- _build_prompt()      --> Construct structured LLM prompt
    +-- _call_llm()          --> Anthropic → OpenAI → Fallback
    +-- _parse_llm_response()--> Extract JSON from LLM output
    |
    v
Patent model (SQLAlchemy) + LLM APIs (Anthropic/OpenAI)
```

## Components

### 1. Idea Generation Service (`src/services/idea_service.py`)

**generate_ideas(cpc_prefix, focus, count, context_text)**
- Gathers seed data from the patent database
- Builds a structured prompt with patent context
- Calls LLM API (Anthropic first, OpenAI fallback, template fallback)
- Parses and normalizes response into structured idea objects

**get_seeds(cpc_prefix)**
- Returns available context data for preview
- Expiring patents (next 2 years, sorted by citation impact)
- Growth areas (top CPC codes by recent filing volume)

**Three Generation Strategies:**
1. `expiring` - Ideas from soon-to-expire patent technologies
2. `combination` - Cross-domain technology combinations
3. `improvement` - Enhancements to highly-cited foundational patents

### 2. LLM Integration

Priority order:
1. **Anthropic Claude** (claude-sonnet-4-20250514) - Primary, uses httpx async client
2. **OpenAI GPT-4o** - Secondary fallback
3. **Template ideas** - Deterministic fallback when no API keys configured

Response parsing handles:
- Raw JSON arrays
- JSON within markdown code blocks (```json ... ```)
- Graceful fallback on parse failure

### 3. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ideas/generate` | POST | Generate invention ideas |
| `/api/ideas/seeds` | GET | Preview available seed data |

### 4. Frontend (`frontend/src/pages/IdeasPage.tsx`)

- Strategy selector (expiring/combination/improvement) with descriptions
- CPC prefix filter for technology focus
- Idea count selector (3/5/8/10)
- Optional context text for additional guidance
- Seed data preview panel showing available patents and trends
- Idea cards with novelty score badges, rationale section, CPC tags

## Design Decisions

1. **Multi-provider LLM with fallback**: Ensures the feature works in any environment - production with API keys gets real generation, development gets deterministic template ideas.

2. **Seed-based prompting**: Grounding LLM generation in actual patent data prevents hallucination and ensures ideas are relevant to the current technology landscape.

3. **Structured JSON output**: Requesting JSON array output with specific keys enables reliable parsing and consistent frontend rendering.

4. **Novelty score clamping**: Scores are clamped to [0, 1] range regardless of LLM output to ensure consistent UI rendering.

5. **Query parameters over body**: Using query params for the generate endpoint allows simple browser/curl testing while keeping the API RESTful.

6. **High-impact patent inclusion**: For combination/improvement strategies, including highly-cited patents provides the LLM with foundational technologies to build upon.

7. **Abstract truncation in prompts**: Limiting abstract length to 200-300 chars per patent keeps the prompt within token limits while providing enough context.
