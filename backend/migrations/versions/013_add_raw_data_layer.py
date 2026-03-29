"""Add Raw Data Layer tables

Revision ID: 013
Revises: 012_add_venue_config
Create Date: 2026-03-26

Changes:
1. Add raw_work table for storing raw work data from OpenAlex
2. Add raw_author table for storing raw author data from OpenAlex
3. Add raw_institution table for storing raw institution data from OpenAlex
4. Add rel_author_tech_belong table for author-tech element relationships
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # RawWork table
    # ============================================
    op.create_table(
        'raw_work',
        sa.Column('raw_work_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_work_id', sa.String(50), nullable=False, unique=True),
        sa.Column('raw_json', sa.Text, nullable=False),
        sa.Column('title', sa.Text, nullable=True),
        sa.Column('doi', sa.String(200), nullable=True),
        sa.Column('publication_year', sa.Integer, nullable=True),
        sa.Column('publication_date', sa.String(20), nullable=True),
        sa.Column('source_id', sa.String(50), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('author_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('author_ids', sa.Text, nullable=True),
        sa.Column('processed_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Column('error_info', sa.Text, nullable=True),
        sa.Column('fetched_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('fetch_task_id', sa.Integer, nullable=True),
        sa.Column('sub_task_id', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_raw_work_openalex', 'raw_work', ['openalex_work_id'])
    op.create_index('ix_raw_work_doi', 'raw_work', ['doi'])
    op.create_index('ix_raw_work_year', 'raw_work', ['publication_year'])
    op.create_index('ix_raw_work_source', 'raw_work', ['source_id'])
    op.create_index('ix_raw_work_status', 'raw_work', ['processed_status'])

    # ============================================
    # RawAuthor table
    # ============================================
    op.create_table(
        'raw_author',
        sa.Column('raw_author_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_author_id', sa.String(50), nullable=False, unique=True),
        sa.Column('raw_json', sa.Text, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('orcid', sa.String(50), nullable=True),
        sa.Column('works_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cited_by_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('h_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('i10_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_known_institution_id', sa.String(50), nullable=True),
        sa.Column('last_known_institution_name', sa.String(255), nullable=True),
        sa.Column('processed_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Column('error_info', sa.Text, nullable=True),
        sa.Column('fetched_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('fetch_task_id', sa.Integer, nullable=True),
        sa.Column('std_author_id', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_raw_author_openalex', 'raw_author', ['openalex_author_id'])
    op.create_index('ix_raw_author_name', 'raw_author', ['display_name'])
    op.create_index('ix_raw_author_orcid', 'raw_author', ['orcid'])
    op.create_index('ix_raw_author_inst', 'raw_author', ['last_known_institution_id'])
    op.create_index('ix_raw_author_status', 'raw_author', ['processed_status'])
    op.create_index('ix_raw_author_std', 'raw_author', ['std_author_id'])

    # ============================================
    # RawInstitution table
    # ============================================
    op.create_table(
        'raw_institution',
        sa.Column('raw_institution_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_institution_id', sa.String(50), nullable=False, unique=True),
        sa.Column('raw_json', sa.Text, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('country_code', sa.String(10), nullable=True),
        sa.Column('country_name', sa.String(100), nullable=True),
        sa.Column('ror', sa.String(50), nullable=True),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('processed_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Column('error_info', sa.Text, nullable=True),
        sa.Column('fetched_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('fetch_task_id', sa.Integer, nullable=True),
        sa.Column('std_school_id', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_raw_inst_openalex', 'raw_institution', ['openalex_institution_id'])
    op.create_index('ix_raw_inst_name', 'raw_institution', ['display_name'])
    op.create_index('ix_raw_inst_country', 'raw_institution', ['country_code'])
    op.create_index('ix_raw_inst_status', 'raw_institution', ['processed_status'])
    op.create_index('ix_raw_inst_std', 'raw_institution', ['std_school_id'])

    # ============================================
    # AuthorTechBelong table
    # ============================================
    op.create_table(
        'rel_author_tech_belong',
        sa.Column('belong_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('openalex_author_id', sa.String(50), nullable=False),
        sa.Column('std_author_id', sa.Integer, nullable=True),
        sa.Column('tech_element_id', sa.Integer, nullable=False),
        sa.Column('source_venue_id', sa.Integer, nullable=True),
        sa.Column('work_count_in_venue', sa.Integer, nullable=False, server_default='0'),
        sa.Column('first_work_year', sa.Integer, nullable=True),
        sa.Column('last_work_year', sa.Integer, nullable=True),
        sa.Column('source_task_id', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_author_tech_belong', 'rel_author_tech_belong', ['openalex_author_id', 'tech_element_id'], unique=True)
    op.create_index('ix_author_tech_author', 'rel_author_tech_belong', ['openalex_author_id'])
    op.create_index('ix_author_tech_tech', 'rel_author_tech_belong', ['tech_element_id'])
    op.create_index('ix_author_tech_venue', 'rel_author_tech_belong', ['source_venue_id'])

    # Foreign keys
    op.create_foreign_key('fk_raw_work_task', 'raw_work', 'sync_collect_task', ['fetch_task_id'], ['task_id'])
    op.create_foreign_key('fk_raw_work_subtask', 'raw_work', 'sync_venue_sub_task', ['sub_task_id'], ['sub_task_id'])
    op.create_foreign_key('fk_raw_author_task', 'raw_author', 'sync_collect_task', ['fetch_task_id'], ['task_id'])
    op.create_foreign_key('fk_raw_inst_task', 'raw_institution', 'sync_collect_task', ['fetch_task_id'], ['task_id'])
    op.create_foreign_key('fk_author_tech_tech', 'rel_author_tech_belong', 'core_tech_element', ['tech_element_id'], ['tech_element_id'])
    op.create_foreign_key('fk_author_tech_venue', 'rel_author_tech_belong', 'config_venue', ['source_venue_id'], ['venue_id'])
    op.create_foreign_key('fk_author_tech_task', 'rel_author_tech_belong', 'sync_collect_task', ['source_task_id'], ['task_id'])


def downgrade():
    op.drop_constraint('fk_author_tech_task', 'rel_author_tech_belong', type_='foreignkey')
    op.drop_constraint('fk_author_tech_venue', 'rel_author_tech_belong', type_='foreignkey')
    op.drop_constraint('fk_author_tech_tech', 'rel_author_tech_belong', type_='foreignkey')
    op.drop_constraint('fk_raw_inst_task', 'raw_institution', type_='foreignkey')
    op.drop_constraint('fk_raw_author_task', 'raw_author', type_='foreignkey')
    op.drop_constraint('fk_raw_work_subtask', 'raw_work', type_='foreignkey')
    op.drop_constraint('fk_raw_work_task', 'raw_work', type_='foreignkey')

    op.drop_table('rel_author_tech_belong')
    op.drop_table('raw_institution')
    op.drop_table('raw_author')
    op.drop_table('raw_work')
