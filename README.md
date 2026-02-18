# Patent Intelligence

AI-powered patent intelligence platform for discovering expiring patents, white space opportunities, and innovation ideas from 200M+ global patents.

## Live Demo

**Production:** [https://patent-intelligence.onrender.com](https://patent-intelligence.onrender.com)

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Semantic Patent Search** | AI-powered search using PatentSBERTa embeddings across 200M+ patents with natural language queries |
| **Expiration Intelligence** | Track patent expirations, maintenance fees, grace periods, and discover lapsed patent opportunities |
| **White Space Discovery** | Identify technology gaps, abandoned goldmines, dormant areas, and cross-domain innovation opportunities |
| **AI Idea Generation** | LLM-powered invention suggestions from expiring patents, technology combinations, and improvement opportunities |
| **Citation Network Analysis** | Technology trajectory mapping, citation trees, and prior art discovery |
| **Trend Analysis** | CPC-based technology trends, growth rate analysis, and competitive landscape insights |
| **Patent Similarity** | Find similar patents using vector embeddings with configurable similarity thresholds |
| **Watchlist & Alerts** | Track patents, CPC codes, assignees with automated expiration and maintenance fee alerts |

### Dashboard

Real-time intelligence dashboard showing:
- Patent database statistics and expiration forecasts
- System component health (API, database, ingestion services)
- Unread alert counts and priority breakdown
- Top trending CPC technology areas
- Quick navigation to all features

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │         Frontend (React/Vite)       │
                                    │   Landing │ Dashboard │ Features    │
                                    └──────────────────┬──────────────────┘
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Search  │ │Expiration│ │Whitespace│ │  Ideas   │ │    Watchlist     │   │
│  │  Routes  │ │  Routes  │ │  Routes  │ │  Routes  │ │     Routes       │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
│       │            │            │            │                 │             │
│       ▼            ▼            ▼            ▼                 ▼             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         Service Layer                                 │   │
│  │  SearchService │ ExpirationService │ WhitespaceService │ IdeaService │   │
│  │  PatentService │ SimilarityService │ WatchlistService  │ StatsService│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  PostgreSQL  │  │    Redis     │  │  LLM APIs    │
            │  + pgvector  │  │   (Cache)    │  │Claude/OpenAI │
            └──────┬───────┘  └──────────────┘  └──────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼
┌─────────┐  ┌─────────┐
│  USPTO  │  │   EPO   │
│Ingester │  │Ingester │
└─────────┘  └─────────┘
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Celery |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Lucide Icons |
| **Database** | PostgreSQL 16 with pgvector extension (768-dim) for vector similarity search |
| **AI/ML** | PatentSBERTa embeddings (768-dim), Claude Sonnet / GPT-4o for idea generation |
| **Caching** | Redis for session cache and rate limiting |
| **Infrastructure** | Docker, GitHub Actions CI/CD, Render deployment |
| **Testing** | pytest, pytest-asyncio, pytest-cov |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+ with pgvector extension

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/patent-intelligence.git
cd patent-intelligence

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d db redis

# Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.api.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

The application will be available at:
- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_watchlist_service.py -v
```

### Docker (Full Stack)

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/patents` | GET | List patents with pagination and filters |
| `/api/patents/{patent_number}` | GET | Get patent details by patent number |
| `/api/patents/stats/overview` | GET | Patent counts overview |
| `/api/search` | POST | Semantic/fulltext/hybrid search |

### Authentication & Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register user with email/password |
| `/api/auth/login` | POST | Login and receive JWT access token |
| `/api/auth/me` | GET | Current authenticated user profile |
| `/api/auth/preferences` | GET/PATCH | Read or update user preferences |
| `/api/auth/organizations` | POST | Create a team organization |
| `/api/auth/organizations/{id}/invites` | POST | Invite collaborator by email |
| `/api/auth/invites/{token}/accept` | POST | Accept organization invite |
| `/api/auth/sso/google/start` | GET | Google OAuth2 stub flow start |
| `/api/auth/sso/microsoft/start` | GET | Microsoft OAuth2 stub flow start |

### Expiration Intelligence

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/expiration/dashboard` | GET | Dashboard aggregates |
| `/api/expiration/upcoming` | GET | Patents expiring within timeframe |
| `/api/expiration/maintenance-fees` | GET | Upcoming maintenance fees |
| `/api/expiration/lapsed` | GET | Recently lapsed patents |
| `/api/expiration/stats` | GET | Expiration statistics |

### Similarity & Prior Art

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/similarity/similar` | POST | Find similar patents |
| `/api/similarity/prior-art` | POST | Prior art search |
| `/api/similarity/landscape/{patent_number}` | GET | Patent landscape |

### White Space Discovery

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/whitespace/coverage` | GET | CPC section coverage analysis |
| `/api/whitespace/gaps` | GET | Technology gap opportunities |
| `/api/whitespace/cross-domain/{source_cpc}` | GET | Cross-domain combinations |
| `/api/whitespace/sections` | GET | Section overview details |

### AI Idea Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ideas/generate` | POST | Generate invention ideas |
| `/api/ideas/seeds` | GET | Preview available seed data |

### Analysis & Trends

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analysis/trends` | GET | CPC technology trends |
| `/api/analysis/citations/{patent_number}` | GET | Citation network for patent |
| `/api/analysis/citations/{patent_number}/stats` | GET | Citation summary stats |

### Watchlist & Alerts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchlist` | GET/POST | List or add watchlist items |
| `/api/watchlist/{id}` | PATCH/DELETE | Update or remove item |
| `/api/watchlist/alerts` | GET | List user alerts |
| `/api/watchlist/alerts/summary` | GET | Alert counts by type/priority |
| `/api/watchlist/alerts/{id}/read` | POST | Mark alert as read |
| `/api/watchlist/alerts/{id}/dismiss` | POST | Dismiss alert |
| `/api/watchlist/generate-alerts` | POST | Generate alerts (admin/cron) |

### Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingestion/trigger` | POST | Trigger ingestion job |
| `/api/ingestion/status` | GET | Ingestion status and history |
| `/api/ingestion/jobs/{job_id}` | GET | Ingestion job detail |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Basic health check |
| `/api/health/detailed` | GET | Detailed component health |
| `/api/stats` | GET | Dashboard statistics |
| `/api/status` | GET | Component health status |

## Data Sources

| Source | Coverage | Patent Count | Cost |
|--------|----------|--------------|------|
| USPTO Bulk Data | US patents since 1976 | 8M+ | Free |
| USPTO PatentsView | Disambiguated entities | 50+ years | Free |
| EPO DOCDB | 90+ countries | 90M+ | Free |
| EPO INPADOC | Legal status, families | Global | Free |

## Project Structure

```
patent-intelligence/
├── src/
│   ├── api/
│   │   ├── main.py           # FastAPI application
│   │   ├── routes/           # API route handlers
│   │   │   ├── patents.py
│   │   │   ├── search.py
│   │   │   ├── expiration.py
│   │   │   ├── similarity.py
│   │   │   ├── analysis.py
│   │   │   ├── whitespace.py
│   │   │   ├── ideas.py
│   │   │   ├── watchlist.py
│   │   │   ├── ingestion.py
│   │   │   └── health.py
│   │   └── schemas/          # Pydantic request/response models
│   ├── ai/                   # ML/embedding services
│   │   ├── embeddings.py
│   │   └── search_service.py
│   ├── services/             # Business logic layer
│   │   ├── citation_service.py
│   │   ├── expiration_service.py
│   │   ├── idea_service.py
│   │   ├── similarity_service.py
│   │   ├── stats_service.py
│   │   ├── watchlist_service.py
│   │   └── whitespace_service.py
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── patent.py
│   │   ├── watchlist.py
│   │   └── ingestion.py
│   ├── ingesters/            # Data source connectors
│   │   ├── uspto_ingester.py
│   │   ├── epo_ingester.py
│   │   └── epo_client.py
│   ├── pipeline/             # Celery pipeline tasks
│   │   ├── orchestrator.py
│   │   ├── expiration_calc.py
│   │   └── patent_store.py
│   ├── database/             # DB engine and init scripts
│   │   ├── connection.py
│   │   └── init.sql
│   └── utils/                # Shared utilities
│       ├── logger.py
│       └── rate_limiter.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Router configuration
│   │   ├── pages/            # Page components
│   │   │   ├── Landing.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   ├── ExpirationPage.tsx
│   │   │   ├── WhiteSpacePage.tsx
│   │   │   ├── IdeasPage.tsx
│   │   │   ├── TrendsPage.tsx
│   │   │   ├── SimilarityPage.tsx
│   │   │   └── WatchlistPage.tsx
│   │   └── components/       # Reusable components
│   └── vite.config.ts
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests (if present)
│   └── conftest.py           # pytest fixtures
├── docs/
│   └── sdd/                  # Software Design Documents
│       ├── phase-3/          # Search Engine
│       ├── phase-4/          # Expiration Intelligence
│       ├── phase-5/          # EPO Integration
│       ├── phase-6/          # Similarity & Prior Art
│       ├── phase-7/          # Citations & Trends
│       ├── phase-8/          # AI Idea Generation
│       ├── phase-9/          # White Space Discovery
│       └── phase-10/         # Watchlist & Alerts
├── alembic/                  # Database migrations
├── docker-compose.yml
├── Dockerfile
├── render.yaml               # Render deployment config
└── requirements.txt
```

## Development Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Core Infrastructure & Web Foundation | Complete |
| 2 | USPTO Data Ingestion Pipeline | Complete |
| 3 | Patent Search Engine | Complete |
| 4 | Expiration Intelligence | Complete |
| 5 | EPO International Data Integration | Complete |
| 6 | Patent Similarity & Prior Art | Complete |
| 7 | Citation Network & Trend Analysis | Complete |
| 8 | AI-Powered Idea Generation | Complete |
| 9 | White Space Discovery | Complete |
| 10 | Watchlist, Alerts & Production Polish | Complete |

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/patents

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM APIs (optional - enables AI idea generation)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# USPTO API (optional - for real-time data)
USPTO_API_KEY=...

# EPO API (optional - for European patents)
EPO_CONSUMER_KEY=...
EPO_CONSUMER_SECRET=...
```

## Deployment

### Render (Production)

The application is configured for Render deployment via `render.yaml`:

```yaml
services:
  - type: web
    name: patent-intelligence-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT

  - type: web
    name: patent-intelligence-frontend
    runtime: static
    buildCommand: cd frontend && npm ci && npm run build
    staticPublishPath: frontend/dist
```

### Docker Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Coming Soon: Voice Patent Research

**Powered by PersonaPlex Full Duplex AI**

Transform how you research patents with natural voice conversation. Ask questions, explore results, and navigate the patent landscape hands-free.

### Current Experience
```
Type search query → Click search → Read results → Click patent → Type new query
```

### With PersonaPlex
```
You: "Show me patents for electric vehicle battery cooling"
PersonaPlex: "Found 2,340 results. Want me to filter by expiration date or assignee?"
You: "Show ones expiring in the next 2 years"
PersonaPlex: "142 patents expiring soon. The top one is from Tesla, filed in 2017..."
You: "What's the white space in this area?"
PersonaPlex: "I see gaps in thermal management for solid-state batteries. Want me to generate invention ideas?"
```

### Features

| Feature | Description |
|---------|-------------|
| **Voice Search** | Search patents by speaking naturally |
| **Conversational Navigation** | Ask follow-up questions to refine results |
| **Hands-Free Analysis** | Have patents read aloud while you work |
| **Voice Alerts** | Get spoken updates on watched patents |
| **Idea Dictation** | Capture invention ideas by voice |

### Technical Requirements

- 24GB+ VRAM (Mac M2 Pro or higher)
- 32GB RAM recommended
- Runs 100% locally - no cloud required
- <500ms response time

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [PatentSBERTa](https://huggingface.co/AI-Growth-Lab/PatentSBERTa) for patent-specific embeddings
- [USPTO](https://www.uspto.gov/) for open patent data
- [EPO Open Patent Services](https://www.epo.org/searching-for-patents/data/web-services/ops.html) for international patent data
