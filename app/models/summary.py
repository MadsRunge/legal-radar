"""Pydantic schemas for AI-generated document summaries."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SummaryBase(BaseModel):
    """Shared summary fields."""

    document_id: UUID = Field(..., description="UUID of the source document")
    summary_text: str = Field(..., description="AI-generated plain-language summary")
    novelty_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0–1 score indicating how novel/impactful this document is",
    )
    principial: bool = Field(
        default=False,
        description="True if this is a principial (landmark) decision",
    )
    affected_laws: list[str] = Field(
        default_factory=list,
        description="List of law identifiers amended or referenced",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Extracted keywords for search and filtering",
    )


class SummaryCreate(SummaryBase):
    """Schema for storing a new AI summary."""


class Summary(SummaryBase):
    """Full summary schema including server-assigned fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
