"""Add cs_concepts_score to StdAuthor

Revision ID: 021
Revises: 020
Create Date: 2026-03-31

NOTE: Existing records will have cs_concepts_score = 0.0 by default.
      This means they will be filtered out during sync (threshold = 0.3).
      To recalculate scores for existing records, run:
        python scripts/recalculate_cs_scores.py
      Or re-normalize the raw authors for the task.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cs_concepts_score column to std_author table
    op.add_column(
        'std_author',
        sa.Column('cs_concepts_score', sa.Float(), nullable=True, default=0.0)
    )


def downgrade() -> None:
    # Remove cs_concepts_score column from std_author table
    op.drop_column('std_author', 'cs_concepts_score')
