"""Business logic for document asset persistence and retrieval."""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentAssetORM
from app.models.document_asset import DocumentAsset, DocumentAssetCreate


async def create_document_asset(
    session: AsyncSession,
    document_id: uuid.UUID,
    asset: DocumentAssetCreate,
) -> DocumentAsset:
    """Persist a new document asset linked to a document.

    Args:
        session: Active async DB session.
        document_id: UUID of the parent document.
        asset: Validated DocumentAssetCreate payload.

    Returns:
        Persisted DocumentAsset with server-assigned fields.
    """
    orm_obj = DocumentAssetORM(
        document_id=document_id,
        external_id=asset.external_id,
        source_entity=asset.source_entity,
        relation_type=asset.relation_type,
        title=asset.title,
        url=asset.url,
        mime_type=asset.mime_type,
        text_content=asset.text_content,
        publication_date=asset.publication_date,
    )
    session.add(orm_obj)
    await session.flush()
    await session.refresh(orm_obj)
    logger.debug("Document asset created", id=str(orm_obj.id), document_id=str(document_id))
    return DocumentAsset.model_validate(orm_obj)


async def list_document_assets(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentAsset]:
    """Return all assets for a given document.

    Args:
        session: Active async DB session.
        document_id: UUID of the parent document.

    Returns:
        List of DocumentAsset instances.
    """
    result = await session.execute(
        select(DocumentAssetORM).where(DocumentAssetORM.document_id == document_id)
    )
    rows = result.scalars().all()
    return [DocumentAsset.model_validate(r) for r in rows]
