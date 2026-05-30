"""add_character_killmails

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'character_killmails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('killmail_id', sa.BigInteger(), nullable=False),
        sa.Column('killmail_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('is_loss', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('ship_type_id', sa.Integer(), nullable=True),
        sa.Column('solar_system_id', sa.BigInteger(), nullable=True),
        sa.Column('killmail_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attacker_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_value', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id', 'killmail_id', name='uq_char_killmail'),
    )
    op.create_index('ix_character_killmails_character_id', 'character_killmails', ['character_id'])
    op.create_index('ix_character_killmails_killmail_time', 'character_killmails', ['killmail_time'])


def downgrade() -> None:
    op.drop_index('ix_character_killmails_killmail_time', table_name='character_killmails')
    op.drop_index('ix_character_killmails_character_id', table_name='character_killmails')
    op.drop_table('character_killmails')
