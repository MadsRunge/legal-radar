"""Add external_id/source_entity/document_kind/source_metadata to documents + document_assets table

Revision ID: 002
Revises: 001
Create Date: 2026-03-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on documents
    op.add_column("documents", sa.Column("external_id", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("source_entity", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("document_kind", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("source_metadata", JSONB(), nullable=True))
    op.create_index("ix_documents_external_id", "documents", ["external_id"])

    # New document_assets table
    op.create_table(
        "document_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("source_entity", sa.String(100), nullable=False),
        sa.Column("relation_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_document_assets_document_id", "document_assets", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_assets")
    op.drop_index("ix_documents_external_id", table_name="documents")
    op.drop_column("documents", "source_metadata")
    op.drop_column("documents", "document_kind")
    op.drop_column("documents", "source_entity")
    op.drop_column("documents", "external_id")
