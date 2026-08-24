"""add pgvector embedding columns

Revision ID: a1b2c3d4e5f6
Revises: 49fc513fd9dc
Create Date: 2026-08-23 13:00:00.000000

Enables real vector similarity search for tickets and KB articles by giving
each embedding table a pgvector ``embedding`` column plus an HNSW index.
Production deployments run this via ``alembic upgrade head``; environments
without the extension degrade gracefully in the vector_store layer.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '49fc513fd9dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    # pgvector is optional in local/dev environments. If the extension is not
    # installed on the PostgreSQL server, keep the schema upgrade moving and
    # let the application degrade gracefully without vector search.
    try:
        with op.get_context().autocommit_block():
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        return

    # Ticket embeddings.
    op.execute(
        f"ALTER TABLE ticket_embeddings "
        f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM})"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_embeddings_embedding "
        "ON ticket_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

    # KB article embeddings.
    op.execute(
        f"ALTER TABLE kb_article_embeddings "
        f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM})"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_embedding_article_embedding "
        "ON kb_article_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ticket_embeddings_embedding")
    op.execute("DROP INDEX IF EXISTS ix_kb_embedding_article_embedding")
    op.execute("ALTER TABLE ticket_embeddings DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE kb_article_embeddings DROP COLUMN IF EXISTS embedding")
