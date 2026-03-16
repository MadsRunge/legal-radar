"""Business logic for document retrieval and persistence."""

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentORM
from app.models.document import Document, DocumentCreate, DocumentListResponse


async def get_document_by_id(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> Document | None:
    """Fetch a single document by its UUID.

    Args:
        session: Active async DB session.
        document_id: UUID of the document.

    Returns:
        Parsed Document or None if not found.
    """
    result = await session.execute(
        select(DocumentORM).where(DocumentORM.id == document_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return Document.model_validate(row)


async def list_documents(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    legal_area: str | None = None,
    principial_only: bool = False,
) -> DocumentListResponse:
    """Return a paginated list of documents with optional filters.

    Args:
        session: Active async DB session.
        page: 1-based page number.
        page_size: Number of results per page (max 100).
        legal_area: Filter by legal area when provided.
        principial_only: When True, only return principial documents.

    Returns:
        Paginated DocumentListResponse.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    query: Any = select(DocumentORM)
    count_query: Any = select(func.count()).select_from(DocumentORM)

    if legal_area:
        query = query.where(DocumentORM.legal_area == legal_area)
        count_query = count_query.where(DocumentORM.legal_area == legal_area)

    # principial_only filter requires a join to summaries — placeholder for now
    if principial_only:
        logger.debug("principial_only filter is a stub — implement via SummaryORM join")

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    result = await session.execute(
        query.order_by(DocumentORM.publication_date.desc()).offset(offset).limit(page_size)
    )
    rows = result.scalars().all()

    return DocumentListResponse(
        items=[Document.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def create_document(
    session: AsyncSession,
    data: DocumentCreate,
) -> Document:
    """Persist a new document.

    Args:
        session: Active async DB session.
        data: Validated DocumentCreate payload.

    Returns:
        Persisted Document with server-assigned fields.
    """
    orm_obj = DocumentORM(
        title=data.title,
        source=data.source,
        url=str(data.url),
        publication_date=data.publication_date,
        legal_area=data.legal_area,
        raw_text=data.raw_text,
    )
    session.add(orm_obj)
    await session.flush()  # populate id + timestamps without committing
    await session.refresh(orm_obj)
    logger.info("Document created", id=str(orm_obj.id), title=orm_obj.title)
    return Document.model_validate(orm_obj)
