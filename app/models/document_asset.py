"""Pydantic schemas for document assets."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentAssetBase(BaseModel):
    """Shared fields for document asset creation and retrieval."""

    external_id: str | None = None
    source_entity: str
    relation_type: str
    title: str | None = None
    url: str | None = None
    mime_type: str | None = None
    text_content: str | None = None
    publication_date: date | None = None


class DocumentAssetCreate(DocumentAssetBase):
    """Schema for creating a new document asset."""


class DocumentAsset(DocumentAssetBase):
    """Full document asset schema including server-assigned fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    created_at: datetime
