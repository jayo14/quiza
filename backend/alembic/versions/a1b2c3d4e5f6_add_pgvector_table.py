"""add pgvector table for postgresql

Revision ID: a1b2c3d4e5f6
Revises: 08e7f1615d2b
Create Date: 2026-09-04 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '08e7f1615d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        op.execute("""
            CREATE TABLE IF NOT EXISTS chunk_embeddings_vector (
                chunk_id VARCHAR PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
                material_id VARCHAR NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
                user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                embedding vector(3072) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_user_material
            ON chunk_embeddings_vector (user_id, material_id);
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TABLE IF EXISTS chunk_embeddings_vector;")
