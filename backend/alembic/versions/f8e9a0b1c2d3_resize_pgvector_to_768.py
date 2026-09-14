"""resize pgvector embedding column from 3072 to 768

The default embedding model changed from gemini-embedding-001 (3072 dims)
to text-embedding-004 (768 dims). The old vector(3072) column silently
rejects 768-dim embeddings, causing ingestion to fail with a dimension
mismatch error while chunks get committed without their vectors.

Revision ID: f8e9a0b1c2d3
Revises: f7a8b9c0d1e2
Create Date: 2026-09-14
"""

from alembic import op

revision = "f8e9a0b1c2d3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Clear stale 3072-dim embeddings that can't be used with the new model
    op.execute("DELETE FROM chunk_embeddings_vector")

    # Resize column: vector(3072) -> vector(768)
    op.execute("ALTER TABLE chunk_embeddings_vector ALTER COLUMN embedding TYPE vector(768)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DELETE FROM chunk_embeddings_vector")
    op.execute("ALTER TABLE chunk_embeddings_vector ALTER COLUMN embedding TYPE vector(3072)")
