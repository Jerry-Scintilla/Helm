"""add_task_runs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=False),
        sa.Column("task_name", sa.String(256), nullable=False),
        sa.Column("queue", sa.String(64), nullable=False, server_default="default"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(32), nullable=False, server_default="system"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_runs_task_id", "task_runs", ["task_id"], unique=True)
    op.create_index("ix_task_runs_task_name", "task_runs", ["task_name"])
    op.create_index("ix_task_runs_status", "task_runs", ["status"])
    op.create_index("ix_task_runs_created_at", "task_runs", ["created_at"])
    op.create_index("ix_task_runs_task_name_created", "task_runs", ["task_name", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_task_runs_task_name_created", "task_runs")
    op.drop_index("ix_task_runs_created_at", "task_runs")
    op.drop_index("ix_task_runs_status", "task_runs")
    op.drop_index("ix_task_runs_task_name", "task_runs")
    op.drop_index("ix_task_runs_task_id", "task_runs")
    op.drop_table("task_runs")
