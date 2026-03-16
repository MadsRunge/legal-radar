"""Pydantic schemas for legal documents."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DocumentBase(BaseModel):
    """Shared fields for document creation and retrieval."""

    title: str = Field(..., min_length=1, max_length=500)
    source: str = Field(..., description="Name of the originating source (e.g. EUR-Lex, Lovdata)")
    url: HttpUrl = Field(..., description="Canonical URL of the original document")
    publication_date: date = Field(..., description="Date the document was officially published")
    legal_area: str = Field(..., description="Legal domain (e.g. tax, employment, competition)")
    raw_text: str | None = Field(default=None, description="Full extracted text of the document")
    external_id: int | None = Field(default=None, description="Source-system numeric ID (e.g. ODA Sag.id)")
    source_entity: str | None = Field(default=None, description="Source entity type (e.g. 'Sag', 'Dokument')")
    document_kind: str | None = Field(default=None, description="Document kind (e.g. 'bill', 'judgment')")
    source_metadata: dict | None = Field(default=None, description="Source-specific metadata as JSON")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""


class Document(DocumentBase):
    """Full document schema including server-assigned fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[Document]
    total: int
    page: int
    page_size: int
