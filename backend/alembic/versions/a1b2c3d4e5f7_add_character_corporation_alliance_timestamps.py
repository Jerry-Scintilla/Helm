"""add_character_corporation_alliance_timestamps

Revision ID: a1b2c3d4e5f7
Revises: d3f7a9b2c1e4
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'd3f7a9b2c1e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add corporation_updated_at and alliance_updated_at to characters table."""
    op.add_column('characters', sa.Column('corporation_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('characters', sa.Column('alliance_updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Drop corporation_updated_at and alliance_updated_at columns."""
    op.drop_column('characters', 'corporation_updated_at')
    op.drop_column('characters', 'alliance_updated_at')