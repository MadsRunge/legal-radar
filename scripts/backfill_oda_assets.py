"""Backfill ODA Sagdokument assets for existing Folketing documents.

For each Folketing document with an external_id, fetches related Sagdokument
records from ODA and persists them as DocumentAsset rows. Also updates
raw_text to the richer assembled version.

Idempotent: re-running after a partial failure will only insert assets whose
external_id is not already present for that document.

Run after migrate_v2.py:
  uv run python scripts/backfill_oda_assets.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from loguru import logger
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import DocumentAssetORM, DocumentORM
from app.ingestion.folketing_source import FolketingSource, REQUEST_TIMEOUT
from app.models.document_asset import DocumentAssetCreate
from app.services.document_asset_service import create_document_asset


async def _existing_external_ids(session, document_id) -> set[str]:
    """Return the set of external_ids already stored for this document."""
    result = await session.execute(
        select(DocumentAssetORM.external_id).where(
            DocumentAssetORM.document_id == document_id,
            DocumentAssetORM.external_id.isnot(None),
        )
    )
    return {row for (row,) in result.all()}


async def backfill_document(
    session,
    doc: DocumentORM,
    source: FolketingSource,
    client: httpx.AsyncClient,
) -> int:
    """Fetch and persist missing assets for a single document.

    Returns number of new assets saved (0 if all already present).
    """
    fetched: list[DocumentAssetCreate] = await source._fetch_sag_documents(client, doc.external_id)
    if not fetched:
        logger.debug("No Sagdokument found", sag_id=doc.external_id)
        return 0

    existing_ids = await _existing_external_ids(session, doc.id)
    new_assets = [a for a in fetched if a.external_id not in existing_ids]

    for asset in new_assets:
        await create_document_asset(session, doc.id, asset)

    if new_assets:
        # Update raw_text with richer assembled version using all fetched titles
        all_titles = [a.title for a in fetched if a.title]
        resume = (doc.source_metadata or {}).get("resume") or ""
        if all_titles:
            doc.raw_text = (resume + "\n\n" + "\n".join(all_titles)).strip() or doc.raw_text

    logger.info(
        "Assets backfilled",
        sag_id=doc.external_id,
        doc_id=str(doc.id),
        new=len(new_assets),
        skipped=len(fetched) - len(new_assets),
    )
    return len(new_assets)


async def main() -> None:
    source = FolketingSource()
    total_docs = 0
    total_assets = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentORM).where(
                DocumentORM.source == "folketing",
                DocumentORM.external_id.isnot(None),
            )
        )
        docs = result.scalars().all()
        logger.info("Folketing docs with external_id", count=len(docs))

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            for doc in docs:
                total_docs += 1
                saved = await backfill_document(session, doc, source, client)
                total_assets += saved

        await session.commit()

    logger.info("Backfill complete", docs_processed=total_docs, assets_saved=total_assets)


if __name__ == "__main__":
    asyncio.run(main())
