# Patent Intelligence

AI-powered patent intelligence platform for discovering expiring patents, white space opportunities, and innovation ideas from 200M+ global patents.

## Features

- **Semantic Patent Search** - AI-powered search using PatentSBERTa embeddings across 200M+ patents
- **Expiration Intelligence** - Track patent expirations, maintenance fees, and lapsed patent opportunities
- **White Space Discovery** - Identify gaps in patent coverage and innovation opportunities
- **AI Idea Generation** - LLM-powered invention suggestions from expiring patents and technology combinations
- **Citation Network Analysis** - Technology trajectory mapping and prior art discovery
- **Trend Analysis** - CPC-based technology trends and competitive landscape insights

## Architecture

```
Frontend (React/Vite)  -->  FastAPI Backend  -->  PostgreSQL + pgvector
                                |
                          Celery Workers  -->  Redis
                                |
                    USPTO / EPO / BigQuery Ingesters
```

## Tech Stack

**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Celery, Redis
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, TanStack Query
**Database:** PostgreSQL 16 with pgvector extension
**AI/ML:** PatentSBERTa embeddings, Claude/GPT-4 for idea generation
**Infrastructure:** Docker, GitHub Actions CI/CD, Render deployment

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### Development Setup

```bash
# Clone the repo
git clone <repo-url>
cd patent-intelligence

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d db redis

# Backend setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env

# Run the API
uvicorn src.api.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
pytest tests/
```

### Docker (Full Stack)

```bash
docker compose up --build
```

## API Documentation

Once running, visit: http://localhost:8000/api/docs

## Data Sources

| Source | Coverage | Cost |
|--------|----------|------|
| USPTO Bulk Data | 8M+ US patents | Free |
| USPTO PatentsView | 50+ years, disambiguated | Free |
| EPO DOCDB | 90+ countries | Free |
| EPO INPADOC | Legal status, families | Free |
| Google BigQuery | 90M+ publications | Free tier |

## Project Structure

```
patent-intelligence/
├── src/
│   ├── api/          # FastAPI routes and schemas
│   ├── ai/           # Embedding and ML services
│   ├── ingesters/    # Data source connectors
│   ├── models/       # SQLAlchemy models
│   ├── pipeline/     # ETL orchestration
│   └── utils/        # Shared utilities
├── frontend/         # React/Vite dashboard
├── tests/            # pytest test suite
├── docs/             # Architecture and design docs
└── docker-compose.yml
```

## License

MIT
