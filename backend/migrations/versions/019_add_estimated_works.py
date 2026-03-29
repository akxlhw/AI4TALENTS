"""Add estimated_works field to sync_venue_sub_task

Revision ID: 019
Revises: 018_add_overview_counts
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add estimated_works column to sync_venue_sub_task table
    op.add_column(
        'sync_venue_sub_task',
        sa.Column('estimated_works', sa.Integer(), nullable=True, default=0)
    )


def downgrade() -> None:
    # Remove estimated_works column from sync_venue_sub_task table
    op.drop_column('sync_venue_sub_task', 'estimated_works')
