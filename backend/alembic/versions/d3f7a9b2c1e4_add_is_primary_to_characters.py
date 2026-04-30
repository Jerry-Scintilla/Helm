"""add_is_primary_to_characters

Revision ID: d3f7a9b2c1e4
Revises: c608e1e7ad78
Create Date: 2026-04-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd3f7a9b2c1e4'
down_revision: Union[str, Sequence[str], None] = 'c608e1e7ad78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'))

    # For each user, set their earliest character (by created_at) as primary
    op.execute("""
        UPDATE characters
        SET is_primary = TRUE
        WHERE id IN (
            SELECT DISTINCT ON (user_id) id
            FROM characters
            ORDER BY user_id, created_at ASC
        )
    """)


def downgrade() -> None:
    op.drop_column('characters', 'is_primary')
