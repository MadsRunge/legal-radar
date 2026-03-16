"""SQLAlchemy ORM models."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DocumentORM(Base):
    """Persisted legal document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    publication_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    legal_area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_entity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_kind: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    summaries: Mapped[list["SummaryORM"]] = relationship(
        "SummaryORM", back_populates="document", cascade="all, delete-orphan"
    )
    assets: Mapped[list["DocumentAssetORM"]] = relationship(
        "DocumentAssetORM", back_populates="document", cascade="all, delete-orphan"
    )


class SummaryORM(Base):
    """AI-generated summary attached to a document."""

    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document: Mapped["DocumentORM"] = relationship("DocumentORM", back_populates="summaries")
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, nullable=False)
    principial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affected_laws: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DocumentAssetORM(Base):
    """A source asset (Sagdokument, Fil, etc.) attached to a document."""

    __tablename__ = "document_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document: Mapped["DocumentORM"] = relationship("DocumentORM", back_populates="assets")
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
