"""Add stats_research_topic table for pre-computed hot research topics

Revision ID: 044
Revises: 043_add_user_employee_id
Create Date: 2026-04-29

This migration:
1. Creates stats_research_topic table for pre-computed research topic statistics
2. Creates index on talent_count for efficient Top-N queries
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create stats_research_topic table
    op.create_table(
        'stats_research_topic',
        sa.Column('topic_name', sa.String(255), primary_key=True),
        sa.Column('talent_count', sa.Integer(), nullable=False, default=0),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    # Create index on talent_count for efficient ordering (descending)
    op.create_index(
        'ix_stats_research_topic_count',
        'stats_research_topic',
        [sa.text('talent_count DESC')],
    )


def downgrade() -> None:
    op.drop_index('ix_stats_research_topic_count', table_name='stats_research_topic')
    op.drop_table('stats_research_topic')
