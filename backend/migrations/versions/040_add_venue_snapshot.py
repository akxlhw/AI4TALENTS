"""Add venue_snapshot column to sync_collect_task

Revision ID: 040
Revises: 039
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '040'
down_revision = '039'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add venue_snapshot column to sync_collect_task
    op.add_column(
        'sync_collect_task',
        sa.Column('venue_snapshot', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('sync_collect_task', 'venue_snapshot')
