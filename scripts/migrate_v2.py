"""Database migration v2: add new columns to documents + create document_assets table.

Run once against an existing database to bring it up to the v2 schema:
  uv run python scripts/migrate_v2.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from app.db.database import Base, engine
from app.db import models  # noqa: F401 — registers all ORM models including DocumentAssetORM


ALTER_STATEMENTS = [
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS external_id INTEGER",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_entity VARCHAR(100)",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_kind VARCHAR(100)",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_metadata JSONB",
    "CREATE INDEX IF NOT EXISTS ix_documents_external_id ON documents (external_id)",
]


async def main() -> None:
    async with engine.begin() as conn:
        for stmt in ALTER_STATEMENTS:
            logger.info("Executing", sql=stmt)
            await conn.execute(text(stmt))

        # Create any new tables (document_assets) that don't exist yet
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Migration v2 complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
