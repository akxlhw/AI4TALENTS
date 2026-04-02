"""Remove core_country table, add country columns to core_school

Revision ID: 022
Revises: 021
Create Date: 2026-04-02

This migration:
1. Adds country_code and country_name columns to core_school
2. Drops the country_id foreign key constraint
3. Drops the core_country table

Note: This migration assumes the database has been cleaned or data has been
migrated separately. The country_id column is dropped without data migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add new country columns to core_school
    op.add_column(
        'core_school',
        sa.Column('country_code', sa.String(10), nullable=True, default='XX')
    )
    op.add_column(
        'core_school',
        sa.Column('country_name', sa.String(100), nullable=True)
    )

    # Step 2: Create index on country_code
    op.create_index('ix_core_school_country_code', 'core_school', ['country_code'])

    # Step 3: Drop foreign key constraint (if exists - SQLite may not have it)
    # In SQLite, FK constraints are handled differently
    try:
        op.drop_constraint('fk_core_school_country_id_core_country', 'core_school', type_='foreignkey')
    except Exception:
        # SQLite might not have named FK constraints
        pass

    # Step 4: Drop country_id column from core_school
    op.drop_column('core_school', 'country_id')

    # Step 5: Drop core_country table
    op.drop_table('core_country')


def downgrade() -> None:
    # Step 1: Recreate core_country table
    op.create_table(
        'core_country',
        sa.Column('country_id', sa.Integer(), primary_key=True),
        sa.Column('country_code', sa.String(10), unique=True, nullable=False),
        sa.Column('country_name_cn', sa.String(100), nullable=False),
        sa.Column('country_name_en', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_core_country_country_id', 'core_country', ['country_id'])
    op.create_index('ix_core_country_country_code', 'core_country', ['country_code'])

    # Step 2: Add country_id column back to core_school
    op.add_column(
        'core_school',
        sa.Column('country_id', sa.Integer(), sa.ForeignKey('core_country.country_id'), nullable=True)
    )
    op.create_index('ix_core_school_country_id', 'core_school', ['country_id'])

    # Step 3: Drop country_code and country_name columns
    op.drop_index('ix_core_school_country_code', 'core_school')
    op.drop_column('core_school', 'country_code')
    op.drop_column('core_school', 'country_name')
