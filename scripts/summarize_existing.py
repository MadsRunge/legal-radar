"""Backfill AI summaries for documents that don't have one yet.

Usage:
    uv run python scripts/summarize_existing.py

Requires DEEPSEEK_KEY (or GROK_XAI_KEY) set in .env.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import joinedload  # noqa: E402

from app.ai.summarizer import summarize_document  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.db.database import AsyncSessionLocal  # noqa: E402
from app.db.models import DocumentORM, SummaryORM  # noqa: E402
from app.services.summary_service import create_or_update_summary  # noqa: E402


async def main() -> None:
    settings = get_settings()
    configure_logging(level="INFO")

    logger.info("Starting backfill", env=settings.APP_ENV)

    async with AsyncSessionLocal() as session:
        # Fetch all documents that have no summary yet
        result = await session.execute(
            select(DocumentORM)
            .outerjoin(SummaryORM, DocumentORM.id == SummaryORM.document_id)
            .where(SummaryORM.id.is_(None))
            .order_by(DocumentORM.publication_date.desc())
        )
        docs = result.scalars().all()

    logger.info("Documents without summary", count=len(docs))

    for i, doc in enumerate(docs, start=1):
        logger.info("Summarizing", progress=f"{i}/{len(docs)}", title=doc.title[:80])
        try:
            ai_result = await summarize_document(doc.raw_text or "", doc.title)
            async with AsyncSessionLocal() as session:
                await create_or_update_summary(session, doc.id, ai_result)
                await session.commit()
            logger.info(
                "Summary saved",
                document_id=str(doc.id),
                novelty=ai_result.novelty_score,
                principial=ai_result.principial,
            )
        except Exception as exc:
            logger.error("Failed to summarize", document_id=str(doc.id), error=str(exc))

    logger.info("Backfill complete", processed=len(docs))


if __name__ == "__main__":
    asyncio.run(main())
