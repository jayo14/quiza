"""fix supabase storage path prefix

Revision ID: f7a8b9c0d1e2
Revises: 08e7f1615d2b
Create Date: 2026-09-13 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "08e7f1615d2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE materials SET storage_path = regexp_replace(storage_path, '^materials/', '') "
        "WHERE storage_path LIKE 'materials/%'"
    )


def downgrade() -> None:
    pass
