# Legal Radar — Architecture

## 1. Project Vision

Legal Radar is an AI-powered legal monitoring platform for lawyers and compliance professionals. Its core premise is that the law changes constantly — new legislation is enacted, executive orders are issued, courts hand down precedent-setting decisions — and tracking these developments manually across official sources is slow, incomplete, and expensive.

Traditional legal databases such as Karnov or Westlaw are excellent **reference tools**: you go there when you already know what you are looking for. They are not designed to **alert you** to things you did not know you needed to know. Legal Radar inverts this model. It continuously monitors the authoritative legal sources, detects new developments, and surfaces the ones that matter — with an AI-generated summary, a novelty score, and a flag for principial (precedent-setting) decisions.

The initial focus is **Danish environmental law**, an area with high regulatory velocity across multiple agencies: the legislature (Folketing), the executive gazette (Retsinformation), the environmental appeals board (Miljø- og Fødevareklagenævnet), and the courts (Domsdatabasen).

The long-term vision is a configurable monitoring service where firms and in-house legal teams define the legal areas they care about, and Legal Radar handles the rest.

---

## 2. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Legal Sources                          │
│  Retsinformation · Folketing · Domsdatabasen · MFKN         │
└─────────────┬───────────────────────────────────────────────┘
              │  RSS / REST API / HTML scraping
              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Ingestion Pipeline                        │
│  Source adapters → deduplication → raw text extraction      │
└─────────────┬───────────────────────────────────────────────┘
              │  DocumentCreate
              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PostgreSQL                             │
│  documents table · summaries table                          │
└──────┬──────────────────────────────────┬───────────────────┘
       │  trigger (async, non-blocking)   │  read
       ▼                                  ▼
┌──────────────────┐           ┌──────────────────────────────┐
│   AI Analysis    │           │       FastAPI Backend        │
│  summariser ·    │           │  /documents · /health        │
│  novelty score · │──────────▶│  pagination · filtering      │
│  principial flag │  Summary  └──────────────┬───────────────┘
└──────────────────┘                          │  HTTP JSON
                                              ▼
                              ┌──────────────────────────────┐
                              │       Dash Dashboard         │
                              │  document table · filters ·  │
                              │  detail panel · badges       │
                              └──────────────────────────────┘
```

The pipeline and the API are **decoupled**: ingestion runs on its own schedule (cron or loop) and writes to the database; the API reads from the database independently. Neither blocks the other.

---

## 3. Repository Structure

```
legal-radar/
│
├── alembic.ini                  # Alembic migration configuration
├── pyproject.toml               # Project metadata and dependencies (uv)
│
├── scripts/
│   ├── init_db.py               # Create all tables from ORM models (first-time setup)
│   ├── run_dev.py               # Starts FastAPI + Dash concurrently for local dev
│   └── run_ingestion.py         # Run the ingestion pipeline once (cron-friendly)
│
└── app/
    ├── main.py                  # FastAPI app factory, CORS, lifespan
    │
    ├── core/
    │   ├── config.py            # Pydantic-settings: env vars, DB URL, feature flags
    │   └── logging.py           # Loguru configuration (structured JSON in prod)
    │
    ├── api/
    │   ├── router.py            # Aggregates all sub-routers into api_router
    │   ├── health.py            # GET /health — liveness check
    │   └── documents.py         # GET /documents, GET /documents/{id}
    │
    ├── models/
    │   ├── document.py          # Pydantic schemas: DocumentBase, Document, DocumentListResponse
    │   └── summary.py           # Pydantic schemas: SummaryBase, Summary, SummaryCreate
    │
    ├── services/
    │   └── document_service.py  # Business logic: list, get, create documents
    │
    ├── db/
    │   ├── database.py          # Async engine, session factory, Base, get_db() dependency
    │   ├── models.py            # SQLAlchemy ORM: DocumentORM, SummaryORM
    │   └── migrations/
    │       ├── env.py           # Alembic env (sync psycopg2, imports Base.metadata)
    │       ├── script.py.mako   # Migration file template
    │       └── versions/
    │           └── 001_add_fk_summary_document.py
    │
    ├── ingestion/
    │   ├── base_source.py           # LegalSource ABC + RawDocument transfer object
    │   ├── pipeline.py              # IngestionPipeline: orchestration, dedup, AI trigger
    │   ├── retsinformation_source.py # Retsinformation RSS (feedparser)
    │   ├── folketing_source.py      # Folketing Open Data API
    │   ├── domsdatabasen_source.py  # Domsdatabasen court decisions
    │   ├── miljoeklagenavn_source.py # MFKN environmental appeals board
    │   ├── rss_monitor.py           # Generic RSS monitoring utility
    │   └── firecrawl_client.py      # Firecrawl wrapper for complex HTML/JS sites
    │
    ├── ai/
    │   └── summarizer.py        # AI analysis: summary, novelty score, principial flag
    │
    └── dashboard/
        └── app.py               # Dash app: layout, callbacks, document table, detail panel
```

**Layer responsibilities:**

| Layer | Responsibility |
|---|---|
| `core/` | Configuration and logging — no business logic |
| `api/` | HTTP interface only — delegates everything to services |
| `services/` | Business logic — the only layer that may combine queries or apply rules |
| `db/` | Persistence — ORM models, migrations, session management |
| `ingestion/` | Data collection — fetches, normalises, and stores raw documents |
| `ai/` | AI analysis — operates on stored documents asynchronously |
| `dashboard/` | Presentation — reads from API, no direct DB access |

---

## 4. Data Ingestion Architecture

Legal data in Denmark is spread across several independent authoritative sources, each with its own format and access method.

| Source | What it provides | Access method |
|---|---|---|
| **Retsinformation** (`retsinformation.dk`) | Laws, executive orders, statutory instruments | RSS feed (feedparser) |
| **Folketing Open Data** | Bills, parliamentary decisions, committee work | REST API (JSON) |
| **Domsdatabasen** | Court decisions from all Danish courts | Web / REST API |
| **Miljø- og Fødevareklagenævnet (MFKN)** | Environmental and food agency appeals | Web scraping (httpx + Firecrawl) |

### Source Adapter Contract

Every source implements the `LegalSource` abstract base class:

```python
class LegalSource(ABC):
    name: str           # unique identifier, e.g. "retsinformation"
    legal_area: str     # default legal classification

    @abstractmethod
    async def fetch_new_documents(self) -> list[RawDocument]: ...
```

The output is always a list of `RawDocument` objects — a simple Pydantic model that carries title, URL, source name, publication date, legal area, and optional raw text. This normalisation means the pipeline is source-agnostic.

### Pipeline Flow

```
For each registered LegalSource:
  │
  ├── fetch_new_documents()
  │     ├── Fetch RSS / API / HTML
  │     ├── Filter by environmental keywords (where applicable)
  │     └── Fetch full document text (HTML → plain text via _TextExtractor)
  │
  ├── For each RawDocument:
  │     ├── Check URL against documents table (deduplication)
  │     ├── If new → create_document() → INSERT INTO documents
  │     └── Trigger async AI summarisation (fire-and-forget)
  │
  └── Commit session
      Return SourceResult (found / saved / skipped / errors)
```

For sites that render content with JavaScript or require complex navigation, `firecrawl_client.py` wraps the Firecrawl API as an alternative to plain httpx fetches.

---

## 5. Database Model

There are two core tables.

### `documents`

Stores every legal document detected by the ingestion pipeline.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `title` | varchar(500) | Indexed |
| `source` | varchar(200) | Source adapter name, indexed |
| `url` | text | Unique — used for deduplication |
| `publication_date` | date | Indexed |
| `legal_area` | varchar(100) | e.g. `environment`, `planning_law`, indexed |
| `raw_text` | text | Full plain-text content, nullable |
| `created_at` | timestamptz | Server default |
| `updated_at` | timestamptz | Server default, updated on write |

### `summaries`

Stores AI-generated analysis for a document.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `document_id` | UUID | FK → `documents.id` ON DELETE CASCADE, indexed |
| `summary_text` | text | AI-generated summary |
| `novelty_score` | float | 0.0–1.0; how novel this development is |
| `principial` | boolean | Whether this is a precedent-setting decision |
| `affected_laws` | varchar[] | List of referenced laws/statutes |
| `keywords` | varchar[] | Extracted topic keywords |
| `created_at` | timestamptz | Server default |

### Relationship

```
documents ──< summaries
  (one)         (many)
```

One document can have multiple summary versions (e.g. if re-processed), but in practice zero or one. The FK uses `ON DELETE CASCADE`: deleting a document automatically removes its summaries.

**Why summaries are stored separately:** AI analysis is expensive, asynchronous, and may not complete in the same transaction as ingestion. Decoupling the tables means a document is immediately queryable after ingestion even if the AI has not yet processed it. It also makes re-running AI analysis easy without touching the document record.

---

## 6. API Layer

The FastAPI backend serves as the data layer for the Dash dashboard (and any future clients). It does not contain business logic — that lives in `services/`.

### Endpoints

```
GET  /health                     — Liveness check
GET  /documents                  — Paginated document list with optional filters
GET  /documents/{document_id}    — Single document by UUID
```

### Query Parameters for `GET /documents`

| Parameter | Type | Description |
|---|---|---|
| `page` | int (default 1) | 1-based page number |
| `page_size` | int (default 20, max 100) | Results per page |
| `legal_area` | string (optional) | Filter by legal area slug |
| `principial_only` | bool (default false) | Only return documents with a principial summary |

When `principial_only=true`, the service joins `documents` with `summaries` on `SummaryORM.principial == True`. Documents with no summary are excluded.

### Response Shape

```json
{
  "items": [{ "id": "...", "title": "...", "legal_area": "environment", ... }],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

### Design Notes

- All database operations are async (asyncpg + SQLAlchemy async session)
- The `get_db()` dependency injects a session per request with automatic commit on success and rollback on exception
- CORS is open in development; all origins are blocked in production (configure allowed origins in `Settings`)

---

## 7. Dashboard Architecture

The Dash dashboard (`app/dashboard/app.py`) is a single-page application that talks exclusively to the FastAPI backend over HTTP — it never accesses the database directly.

### Layout

```
┌───────────────────────────────────────────────────────┐
│  Legal Radar                                          │
│  AI-powered legal monitoring dashboard                │
├───────────────────────────────────────────────────────┤
│  [Legal Area ▼]  [☐ Principial cases only]  [Refresh] │
├───────────────────────────────────────────────────────┤
│  Title │ Source │ Legal Area │ Published │ (ID hidden) │
│  ────────────────────────────────────────────────────  │
│  ...   │ ...    │ ...        │ ...       │             │
├───────────────────────────────────────────────────────┤
│  Detail Panel (shown on row selection)                │
│  ┌──────────────────────────────────────────────┐    │
│  │  [Title]                  [Principial Badge] │    │
│  │  Source · Published · Area                   │    │
│  │  Novelty Score: 72%  ████████░░              │    │
│  │  ──────────────────────────────────          │    │
│  │  Raw text preview (first 500 chars)…         │    │
│  └──────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────┘
```

### Filters

| Filter | Backend parameter |
|---|---|
| Legal Area dropdown | `legal_area` (environment, planning_law, nature_protection, waste_regulation, water_regulation) |
| "Principial cases only" checkbox | `principial_only=true` |

### Data Flow

```
User changes filter / clicks Refresh
  → Dash callback fires
  → httpx.get(API_BASE/documents, params=...)
  → Renders DataTable

User selects a row
  → Dash callback fires
  → httpx.get(API_BASE/documents/{id})
  → httpx.get(API_BASE/documents/{id}/summary)  [optional — 200 if exists]
  → Renders detail panel with badge + novelty bar + raw text preview
```

The dashboard also has a `dcc.Interval` component that auto-refreshes the document table every 5 minutes without user interaction.

---

## 8. AI Analysis Layer (Future Milestone)

The AI layer (`app/ai/summarizer.py`) is the feature that most differentiates Legal Radar from passive legal databases.

After a document is ingested, the pipeline triggers an async summarisation call. The AI layer will produce:

| Output | Description |
|---|---|
| `summary_text` | Plain-language summary of the legal development |
| `novelty_score` | Float 0–1: how novel is this relative to existing law? |
| `principial` | Boolean: does this decision set a new legal precedent? |
| `affected_laws` | Which existing laws or statutes does this reference or modify? |
| `keywords` | Topic keywords for search and filtering |

### Why this matters

A lawyer monitoring environmental law does not need to read every new executive order — most are routine. What they need is to be told *when something changes the legal landscape*. The novelty score and principial flag do exactly that: they let the dashboard surface the 5% of documents that actually require attention, rather than presenting an undifferentiated stream of 100%.

This is the core value proposition that traditional tools lack: Karnov tells you what the law *is*; Legal Radar tells you what *just changed* and *why it matters*.

### Implementation Note

The summariser is called as a fire-and-forget async task from the pipeline. If it fails, the document is still saved and available — AI enrichment is additive, not blocking. This means the ingestion pipeline never stalls waiting for an LLM response.

---

## 9. Development Workflow

### Prerequisites

- Python 3.12+
- PostgreSQL running locally (database: `legal_radar`)
- `uv` installed (`pip install uv` or `brew install uv`)

### Setup

```bash
# 1. Clone and install dependencies
git clone <repo>
cd legal-radar
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, OPENAI_API_KEY, FIRECRAWL_API_KEY as needed

# 3. Create the database
createdb legal_radar

# 4. Initialise schema
uv run python scripts/init_db.py

# 5. Apply migrations
uv run alembic upgrade head
```

### Running the System

```bash
# Start both FastAPI and Dash in one terminal (development mode)
uv run python scripts/run_dev.py

# API available at:  http://localhost:8000
# Dashboard at:      http://localhost:8050
# API docs at:       http://localhost:8000/docs
```

### Running Ingestion

```bash
# Run once (suitable for cron)
uv run python scripts/run_ingestion.py

# Example cron (every 30 minutes):
# */30 * * * * cd /path/to/legal-radar && uv run python scripts/run_ingestion.py
```

### Database Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration (after changing ORM models)
uv run alembic revision --autogenerate -m "describe the change"

# Roll back one migration
uv run alembic downgrade -1
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
uv run ruff check app/       # lint
uv run ruff format app/      # format
uv run mypy app/             # type-check
```
