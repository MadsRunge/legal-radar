"""Service layer for AI-generated document summaries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.summarizer import SummarizationResult
from app.db.models import SummaryORM
from app.models.summary import Summary


async def get_summary(session: AsyncSession, document_id: UUID) -> Summary | None:
    """Return the summary for a document, or None if it doesn't exist."""
    result = await session.execute(
        select(SummaryORM).where(SummaryORM.document_id == document_id).limit(1)
    )
    orm = result.scalar_one_or_none()
    return Summary.model_validate(orm) if orm else None


async def create_or_update_summary(
    session: AsyncSession,
    document_id: UUID,
    result: SummarizationResult,
) -> Summary:
    """Upsert a summary from a SummarizationResult.

    Updates all fields if a summary already exists; inserts otherwise.
    The caller is responsible for committing the session.
    """
    existing = await session.execute(
        select(SummaryORM).where(SummaryORM.document_id == document_id).limit(1)
    )
    orm = existing.scalar_one_or_none()

    if orm is None:
        orm = SummaryORM(document_id=document_id)
        session.add(orm)

    orm.summary_text = result.summary_text
    orm.novelty_score = result.novelty_score
    orm.principial = result.principial
    orm.affected_laws = result.affected_laws
    orm.keywords = result.keywords

    await session.flush()
    return Summary.model_validate(orm)
