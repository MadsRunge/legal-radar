"""Add FK summaries.document_id -> documents.id ON DELETE CASCADE

Revision ID: 001
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create summaries table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL,
            summary_text TEXT NOT NULL,
            novelty_score FLOAT NOT NULL,
            principial BOOLEAN NOT NULL DEFAULT FALSE,
            affected_laws TEXT[] DEFAULT '{}',
            keywords TEXT[] DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Add FK constraint if not already present
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_summaries_document_id'
                  AND table_name = 'summaries'
            ) THEN
                ALTER TABLE summaries
                    ADD CONSTRAINT fk_summaries_document_id
                    FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE;
            END IF;
        END
        $$;
    """)

    # Add index on document_id if not present
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_summaries_document_id ON summaries (document_id);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE summaries
            DROP CONSTRAINT IF EXISTS fk_summaries_document_id;
    """)
