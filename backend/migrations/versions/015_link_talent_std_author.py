"""Link Talent to StdAuthor

Revision ID: 015
Revises: 014_add_standardized_layer
Create Date: 2026-03-26

Changes:
1. Add std_author_id to core_talent table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Add std_author_id column to core_talent
    op.add_column('core_talent', sa.Column('std_author_id', sa.Integer, nullable=True))
    op.create_index('ix_core_talent_std_author', 'core_talent', ['std_author_id'])
    op.create_foreign_key(
        'fk_talent_std_author',
        'core_talent',
        'std_author',
        ['std_author_id'],
        ['std_author_id']
    )


def downgrade():
    op.drop_constraint('fk_talent_std_author', 'core_talent', type_='foreignkey')
    op.drop_index('ix_core_talent_std_author', 'core_talent')
    op.drop_column('core_talent', 'std_author_id')
