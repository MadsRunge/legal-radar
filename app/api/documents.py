"""Document API endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.db.database import DBSession
from app.models.document import Document, DocumentListResponse
from app.services.document_service import get_document_by_id, list_documents

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
