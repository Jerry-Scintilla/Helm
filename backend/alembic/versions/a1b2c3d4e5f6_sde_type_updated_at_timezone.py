"""sde_type updated_at use timestamptz

Revision ID: a1b2c3d4e5f6
Revises: f4fe5a7e15dd
Create Date: 2026-04-28 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4fe5a7e15dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'sde_type',
        'updated_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using='updated_at AT TIME ZONE \'UTC\'',
    )


def downgrade() -> None:
    op.alter_column(
        'sde_type',
        'updated_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using='updated_at AT TIME ZONE \'UTC\'',
    )
