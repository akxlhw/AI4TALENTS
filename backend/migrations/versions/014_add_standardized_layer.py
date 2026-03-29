"""Add Standardized Layer tables

Revision ID: 014
Revises: 013_add_raw_data_layer
Create Date: 2026-03-26

Changes:
1. Add std_author table for normalized author data
2. Add std_school table for normalized school data
3. Add std_school_alias table for school name matching
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # StdSchool table
    # ============================================
    op.create_table(
        'std_school',
        sa.Column('std_school_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_institution_id', sa.String(50), nullable=True, unique=True),
        sa.Column('name_normalized', sa.String(255), nullable=False),
        sa.Column('name_aliases', sa.Text, nullable=True),
        sa.Column('country_id', sa.Integer, nullable=True),
        sa.Column('country_code', sa.String(10), nullable=True),
        sa.Column('country_name', sa.String(100), nullable=True),
        sa.Column('ror', sa.String(50), nullable=True),
        sa.Column('inst_type', sa.String(50), nullable=True),
        sa.Column('homepage_url', sa.String(500), nullable=True),
        sa.Column('confirm_status', sa.String(20), nullable=False, server_default='auto_identified'),
        sa.Column('school_id', sa.Integer, nullable=True),
        sa.Column('source_task_id', sa.Integer, nullable=True),
        sa.Column('normalized_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_std_school_openalex', 'std_school', ['openalex_institution_id'])
    op.create_index('ix_std_school_name', 'std_school', ['name_normalized'])
    op.create_index('ix_std_school_country', 'std_school', ['country_id'])
    op.create_index('ix_std_school_country_code', 'std_school', ['country_code'])
    op.create_index('ix_std_school_status', 'std_school', ['confirm_status'])
    op.create_index('ix_std_school_school', 'std_school', ['school_id'])
    op.create_foreign_key('fk_std_school_country', 'std_school', 'core_country', ['country_id'], ['country_id'])
    op.create_foreign_key('fk_std_school_school', 'std_school', 'core_school', ['school_id'], ['school_id'])

    # ============================================
    # StdAuthor table
    # ============================================
    op.create_table(
        'std_author',
        sa.Column('std_author_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_author_id', sa.String(50), nullable=False, unique=True),
        sa.Column('name_normalized', sa.String(255), nullable=False),
        sa.Column('name_original', sa.String(255), nullable=True),
        sa.Column('orcid', sa.String(50), nullable=True),
        sa.Column('works_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cited_by_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('h_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('i10_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('std_school_id', sa.Integer, nullable=True),
        sa.Column('raw_institution_name', sa.String(255), nullable=True),
        sa.Column('raw_institution_id', sa.String(50), nullable=True),
        sa.Column('confirm_status', sa.String(20), nullable=False, server_default='auto_identified'),
        sa.Column('confidence_score', sa.Float, nullable=False, server_default='0.8'),
        sa.Column('source_task_id', sa.Integer, nullable=True),
        sa.Column('normalized_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_std_author_openalex', 'std_author', ['openalex_author_id'])
    op.create_index('ix_std_author_name', 'std_author', ['name_normalized'])
    op.create_index('ix_std_author_orcid', 'std_author', ['orcid'])
    op.create_index('ix_std_author_school', 'std_author', ['std_school_id'])
    op.create_index('ix_std_author_status', 'std_author', ['confirm_status'])
    op.create_foreign_key('fk_std_author_school', 'std_author', 'std_school', ['std_school_id'], ['std_school_id'])

    # ============================================
    # SchoolNameAlias table
    # ============================================
    op.create_table(
        'std_school_alias',
        sa.Column('alias_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('std_school_id', sa.Integer, nullable=False),
        sa.Column('alias_name', sa.String(255), nullable=False),
        sa.Column('alias_type', sa.String(30), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_school_alias_std', 'std_school_alias', ['std_school_id'])
    op.create_index('ix_school_alias_name', 'std_school_alias', ['alias_name'])
    op.create_foreign_key('fk_school_alias_school', 'std_school_alias', 'std_school', ['std_school_id'], ['std_school_id'])


def downgrade():
    op.drop_table('std_school_alias')
    op.drop_constraint('fk_std_author_school', 'std_author', type_='foreignkey')
    op.drop_table('std_author')
    op.drop_constraint('fk_std_school_school', 'std_school', type_='foreignkey')
    op.drop_constraint('fk_std_school_country', 'std_school', type_='foreignkey')
    op.drop_table('std_school')
