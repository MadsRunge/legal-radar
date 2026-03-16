"""Baseline schema: create documents and summaries tables

Revision ID: 001
Revises:
Create Date: 2026-03-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("legal_area", sa.String(100), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_source", "documents", ["source"])
    op.create_index("ix_documents_publication_date", "documents", ["publication_date"])
    op.create_index("ix_documents_legal_area", "documents", ["legal_area"])

    op.create_table(
        "summaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("principial", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("affected_laws", ARRAY(sa.String()), server_default="{}"),
        sa.Column("keywords", ARRAY(sa.String()), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_summaries_document_id", "summaries", ["document_id"])


def downgrade() -> None:
    op.drop_table("summaries")
    op.drop_table("documents")
