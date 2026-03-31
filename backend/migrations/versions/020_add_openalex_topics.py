"""Add openalex_topics to StdAuthor and Talent

Revision ID: 020
Revises: 019_add_estimated_works
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add openalex_topics column to std_author table
    op.add_column(
        'std_author',
        sa.Column('openalex_topics', sa.JSON(), nullable=True, default=[])
    )

    # Add openalex_topics column to core_talent table
    op.add_column(
        'core_talent',
        sa.Column('openalex_topics', sa.JSON(), nullable=True, default=[])
    )


def downgrade() -> None:
    # Remove openalex_topics column from core_talent table
    op.drop_column('core_talent', 'openalex_topics')

    # Remove openalex_topics column from std_author table
    op.drop_column('std_author', 'openalex_topics')
