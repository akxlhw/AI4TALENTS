"""add country and tech counts to overview stats

Revision ID: 018
Revises: 017
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to stat_overview_snapshot
    op.add_column('stat_overview_snapshot', sa.Column('country_count', sa.Integer(), nullable=True, default=0))
    op.add_column('stat_overview_snapshot', sa.Column('tech_element_count', sa.Integer(), nullable=True, default=0))
    op.add_column('stat_overview_snapshot', sa.Column('tech_direction_count', sa.Integer(), nullable=True, default=0))


def downgrade() -> None:
    op.drop_column('stat_overview_snapshot', 'tech_direction_count')
    op.drop_column('stat_overview_snapshot', 'tech_element_count')
    op.drop_column('stat_overview_snapshot', 'country_count')
