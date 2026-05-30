"""add_character_contracts

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'character_contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.BigInteger(), nullable=False),
        sa.Column('source', sa.String(16), nullable=False, server_default='character'),
        sa.Column('type', sa.String(32), nullable=False, server_default='unknown'),
        sa.Column('status', sa.String(32), nullable=False, server_default=''),
        sa.Column('issuer_id', sa.BigInteger(), nullable=True),
        sa.Column('issuer_corporation_id', sa.BigInteger(), nullable=True),
        sa.Column('assignee_id', sa.BigInteger(), nullable=True),
        sa.Column('acceptor_id', sa.BigInteger(), nullable=True),
        sa.Column('start_location_id', sa.BigInteger(), nullable=True),
        sa.Column('end_location_id', sa.BigInteger(), nullable=True),
        sa.Column('for_corporation', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('availability', sa.String(32), nullable=True),
        sa.Column('title', sa.Text(), nullable=False, server_default=''),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('reward', sa.Float(), nullable=True),
        sa.Column('collateral', sa.Float(), nullable=True),
        sa.Column('buyout', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('days_to_complete', sa.Integer(), nullable=True),
        sa.Column('date_issued', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_expired', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_accepted', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id', 'contract_id', name='uq_char_contract'),
    )
    op.create_index('ix_character_contracts_character_id', 'character_contracts', ['character_id'])
    op.create_index('ix_character_contracts_date_issued', 'character_contracts', ['date_issued'])


def downgrade() -> None:
    op.drop_index('ix_character_contracts_date_issued', table_name='character_contracts')
    op.drop_index('ix_character_contracts_character_id', table_name='character_contracts')
    op.drop_table('character_contracts')
