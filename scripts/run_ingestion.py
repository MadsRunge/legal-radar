"""CLI script to run the ingestion pipeline once.

Usage:
    uv run python scripts/run_ingestion.py

Can be scheduled via cron:
    0 * * * * cd /path/to/legal-radar && uv run python scripts/run_ingestion.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402


async def main() -> int:
    settings = get_settings()
    configure_logging(level="DEBUG" if not settings.is_production else "INFO")

    logger.info("Starting ingestion run", env=settings.APP_ENV)

    pipeline = IngestionPipeline()
    result = await pipeline.run_once()

    if result.total_errors > 0:
        logger.warning(
            "Ingestion completed with errors",
            saved=result.total_saved,
            errors=result.total_errors,
        )
        return 1

    logger.info(
        "Ingestion completed successfully",
        found=result.total_found,
        saved=result.total_saved,
    )
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
