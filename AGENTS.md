# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `app/`. Use `app/api/` for FastAPI routes, `app/services/` for business logic, `app/ingestion/` for source adapters and pipeline code, `app/ai/` for summarization logic, `app/db/` for SQLAlchemy models and Alembic migrations, and `app/dashboard/` for the Dash UI. Operational scripts live in `scripts/` (`run_dev.py`, `run_ingestion.py`, `init_db.py`). Project docs belong in `docs/`; runtime logs go to `logs/`.

## Build, Test, and Development Commands
Use Python 3.12+ with `uv`.

- `uv sync --extra dev` installs runtime and development dependencies.
- `cp .env.example .env` creates local configuration; set `DATABASE_URL` and AI keys before running services.
- `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` starts the API.
- `uv run python -m app.dashboard.app` starts the dashboard.
- `uv run python scripts/run_dev.py` launches API and dashboard together.
- `uv run python scripts/run_ingestion.py` runs one ingestion pass.
- `uv run alembic upgrade head` applies migrations.
- `uv run ruff check .`, `uv run mypy app/`, and `uv run pytest` cover linting, types, and tests.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, type hints on public code, and small focused modules. `ruff` enforces import order and core lint rules; `mypy` runs in strict mode. Keep lines within 100 characters when practical. Use `snake_case` for modules, functions, and variables, `PascalCase` for classes and Pydantic/ORM models, and descriptive filenames such as `retsinformation_source.py`.

## Testing Guidelines
`pytest` is configured with `testpaths = ["tests"]`, so place tests under a top-level `tests/` directory. Name files `test_*.py` and mirror the module under test where possible, for example `tests/ingestion/test_pipeline.py`. Use `pytest-asyncio` for async code. There is no committed test suite yet; new features should include focused tests for API, ingestion, or database behavior they change.

## Commit & Pull Request Guidelines
Current history uses short, descriptive subjects such as `Milestone 2: wire ingestion...`. Prefer imperative, scope-aware commit messages and keep each commit cohesive. Pull requests should summarize user-visible changes, list verification commands run, reference related issues, and include screenshots when dashboard behavior changes.

## Security & Configuration Tips
Do not commit `.env`, secrets, or local database credentials. Keep generated artifacts such as `__pycache__/` out of commits, and review migration files carefully before merging schema changes.
