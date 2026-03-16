"""Document API endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.ai.summarizer import SummarizationResult
from app.db.database import DBSession
from app.models.document import Document, DocumentListResponse
from app.models.document_asset import DocumentAsset
from app.models.summary import Summary, SummaryCreate
from app.services.document_asset_service import list_document_assets
from app.services.document_service import get_document_by_id, list_documents
from app.services.summary_service import create_or_update_summary, get_summary

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def get_documents(
    session: DBSession,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    legal_area: str | None = Query(default=None, description="Filter by legal area"),
    principial_only: bool = Query(default=False, description="Only principial decisions"),
) -> DocumentListResponse:
    """List documents with optional filtering and pagination."""
    return await list_documents(
        session=session,
        page=page,
        page_size=page_size,
        legal_area=legal_area,
        principial_only=principial_only,
    )


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: uuid.UUID,
    session: DBSession,
) -> Document:
    """Retrieve a single document by its UUID."""
    doc = await get_document_by_id(session, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


@router.get("/{document_id}/assets", response_model=list[DocumentAsset])
async def get_document_assets(
    document_id: uuid.UUID,
    session: DBSession,
) -> list[DocumentAsset]:
    """Retrieve stored source assets for a document."""
    doc = await get_document_by_id(session, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return await list_document_assets(session, document_id)


@router.get("/{document_id}/summary", response_model=Summary)
async def get_document_summary(
    document_id: uuid.UUID,
    session: DBSession,
) -> Summary:
    """Retrieve the AI-generated summary for a document."""
    summary = await get_summary(session, document_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="No summary available")
    return summary


@router.post("/{document_id}/summary", response_model=Summary, status_code=201)
async def create_document_summary(
    document_id: uuid.UUID,
    body: SummaryCreate,
    session: DBSession,
) -> Summary:
    """Store or replace an AI summary for a document (admin/internal use)."""
    doc = await get_document_by_id(session, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    result = SummarizationResult(
        summary_text=body.summary_text,
        novelty_score=body.novelty_score,
        principial=body.principial,
        affected_laws=body.affected_laws,
        keywords=body.keywords,
    )
    summary = await create_or_update_summary(session, document_id, result)
    return summary
