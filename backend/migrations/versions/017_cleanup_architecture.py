"""Cleanup architecture - remove redundant fields and tables

Revision ID: 017
Revises: 016
Create Date: 2026-03-28

Changes:
1. Drop collect_sources column from core_tech_element (redundant with VenueTechBinding)
2. Drop raw_source_record table (redundant with RawWork/RawAuthor/RawInstitution)
3. Add indexes on Talent for sorting fields (works_count, h_index, cited_by_count)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop collect_sources column from core_tech_element
    # This field is redundant with VenueTechBinding table
    with op.batch_alter_table('core_tech_element', schema=None) as batch_op:
        batch_op.drop_column('collect_sources')

    # 2. Drop raw_source_record table
    # This table is redundant with RawWork/RawAuthor/RawInstitution
    op.drop_table('raw_source_record')

    # 3. Add indexes on Talent for sorting fields
    with op.batch_alter_table('core_talent', schema=None) as batch_op:
        batch_op.create_index('ix_core_talent_works_count', ['works_count'], unique=False)
        batch_op.create_index('ix_core_talent_h_index', ['h_index'], unique=False)
        batch_op.create_index('ix_core_talent_cited_by_count', ['cited_by_count'], unique=False)


def downgrade():
    # 3. Drop indexes on Talent
    with op.batch_alter_table('core_talent', schema=None) as batch_op:
        batch_op.drop_index('ix_core_talent_cited_by_count')
        batch_op.drop_index('ix_core_talent_h_index')
        batch_op.drop_index('ix_core_talent_works_count')

    # 2. Recreate raw_source_record table
    op.create_table(
        'raw_source_record',
        sa.Column('record_id', sa.INTEGER(), nullable=False),
        sa.Column('batch_id', sa.INTEGER(), nullable=False),
        sa.Column('source_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('source_id', sa.VARCHAR(length=100), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=False),
        sa.Column('processed_status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('processed_at', sa.DATETIME(), nullable=True),
        sa.Column('error_info', sa.TEXT(), nullable=True),
        sa.Column('fetched_at', sa.DATETIME(), nullable=False),
        sa.Column('created_at', sa.DATETIME(), nullable=True),
        sa.Column('updated_at', sa.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('record_id')
    )
    with op.batch_alter_table('raw_source_record', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('batch_id'), ['batch_id'], unique=False)
        batch_op.create_index(batch_op.f('source_type'), ['source_type'], unique=False)
        batch_op.create_index(batch_op.f('source_id'), ['source_id'], unique=False)
        batch_op.create_index(batch_op.f('processed_status'), ['processed_status'], unique=False)

    # 1. Recreate collect_sources column
    with op.batch_alter_table('core_tech_element', schema=None) as batch_op:
        batch_op.add_column(sa.Column('collect_sources', sa.JSON(), nullable=True))
