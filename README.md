# Legal Radar

AI-powered legal monitoring SaaS. Tracks laws, court judgments, and regulations — processes them with AI, and surfaces insights in a real-time dashboard.

## Features

- Automated RSS/feed monitoring for legal sources
- AI-powered document summarization and novelty scoring
- FastAPI backend with async PostgreSQL
- Dash dashboard with filters by legal area and principial cases

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+

## Installation

```bash
# Clone the repo
git clone https://github.com/your-org/legal-radar.git
cd legal-radar

# Install dependencies with uv
uv sync

# Configure environment
cp .env.example .env
# Edit .env and set DATABASE_URL, OPENAI_API_KEY, etc.
```

## Database Setup

```bash
# Create the database
createdb legal_radar

# Run migrations (once Alembic is configured)
uv run alembic upgrade head
```

## Running the API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`.

## Running the Dashboard

```bash
uv run python -m app.dashboard.app
```

Dashboard available at `http://localhost:8050`.

## Running Both (Development)

```bash
uv run python scripts/run_dev.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/documents` | List documents (paginated) |
| GET | `/documents/{id}` | Get document by ID |

## Project Structure

```
legal-radar/
├── app/
│   ├── main.py            # FastAPI app factory
│   ├── core/              # Config + logging
│   ├── api/               # Route handlers
│   ├── models/            # Pydantic schemas
│   ├── services/          # Business logic
│   ├── ingestion/         # RSS + feed monitors
│   ├── ai/                # Summarization + scoring
│   ├── dashboard/         # Dash UI
│   └── db/                # SQLAlchemy ORM + engine
└── scripts/
    └── run_dev.py         # Dev launcher
```

## Development

```bash
# Lint
uv run ruff check .

# Type check
uv run mypy app/

# Tests
uv run pytest
```
