"""Create all database tables from ORM models."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import Base, engine
from app.db import models  # noqa: F401 — ensures ORM models are registered


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
