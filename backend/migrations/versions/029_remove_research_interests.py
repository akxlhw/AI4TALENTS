"""Remove research_interests column from core_talent

Revision ID: 029_remove_research_interests
Revises: 028_add_system_config
Create Date: 2026-04-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove research_interests column - use openalex_topics instead."""
    op.drop_column('core_talent', 'research_interests')


def downgrade() -> None:
    """Add research_interests column back."""
    op.add_column('core_talent', sa.Column('research_interests', sa.Text(), nullable=True))
