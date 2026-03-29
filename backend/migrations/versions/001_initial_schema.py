"""Initial schema with all core tables

Revision ID: 001_initial
Revises:
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if PostgreSQL (skip extensions for SQLite)
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # Enable required extensions (PostgreSQL only)
    if is_postgres:
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Create enum types
    role_type_enum = postgresql.ENUM(
        'professor', 'teaching_research', 'student', 'graduated', 'unknown',
        name='role_type_enum',
        create_type=False
    )
    role_type_enum.create(op.get_bind(), checkfirst=True)

    visibility_status_enum = postgresql.ENUM(
        'active', 'pending', 'hidden',
        name='visibility_status_enum',
        create_type=False
    )
    visibility_status_enum.create(op.get_bind(), checkfirst=True)

    user_role_type_enum = postgresql.ENUM(
        'admin', 'super_admin', 'user',
        name='user_role_type_enum',
        create_type=False
    )
    user_role_type_enum.create(op.get_bind(), checkfirst=True)

    sync_job_status_enum = postgresql.ENUM(
        'pending', 'running', 'success', 'failed', 'partial',
        name='sync_job_status_enum',
        create_type=False
    )
    sync_job_status_enum.create(op.get_bind(), checkfirst=True)

    # ============================================
    # core_country table
    # ============================================
    op.create_table(
        'core_country',
        sa.Column('country_id', sa.Integer(), primary_key=True),
        sa.Column('country_code', sa.String(10), unique=True, nullable=False),
        sa.Column('country_name_cn', sa.String(100), nullable=False),
        sa.Column('country_name_en', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_country_country_code', 'core_country', ['country_code'])
    op.create_index('ix_core_country_sort_order', 'core_country', ['sort_order'])

    # ============================================
    # core_school table
    # ============================================
    op.create_table(
        'core_school',
        sa.Column('school_id', sa.Integer(), primary_key=True),
        sa.Column('school_name', sa.String(255), nullable=False),
        sa.Column('school_alias', sa.String(255), nullable=True),
        sa.Column('country_id', sa.Integer(), sa.ForeignKey('core_country.country_id'), nullable=False),
        sa.Column('school_intro', sa.Text(), nullable=True),
        sa.Column('homepage_url', sa.String(500), nullable=True),
        sa.Column('professor_count', sa.Integer(), default=0),
        sa.Column('student_count', sa.Integer(), default=0),
        sa.Column('is_visible', sa.Boolean(), default=True, nullable=False),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_record_id', sa.String(100), nullable=True),
        sa.Column('last_sync_batch_id', sa.Integer(), nullable=True),
        sa.Column('department_name', sa.String(255), nullable=True),
        sa.Column('lab_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_school_school_name', 'core_school', ['school_name'])
    op.create_index('ix_core_school_country_id', 'core_school', ['country_id'])
    op.create_index('ix_core_school_source_record_id', 'core_school', ['source_record_id'])
    op.create_index('ix_core_school_status_visible', 'core_school', ['status', 'is_visible'])

    # ============================================
    # core_school_alias table
    # ============================================
    op.create_table(
        'core_school_alias',
        sa.Column('alias_id', sa.Integer(), primary_key=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('core_school.school_id'), nullable=False),
        sa.Column('alias_name', sa.String(255), nullable=False),
        sa.Column('alias_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_school_alias_school_id', 'core_school_alias', ['school_id'])
    op.create_index('ix_core_school_alias_alias_name', 'core_school_alias', ['alias_name'])

    # ============================================
    # core_talent table
    # ============================================
    op.create_table(
        'core_talent',
        sa.Column('talent_id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_record_id', sa.String(100), nullable=True),
        sa.Column('last_sync_batch_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_en', sa.String(255), nullable=True),
        sa.Column('orcid', sa.String(50), nullable=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('core_school.school_id'), nullable=True),
        sa.Column('current_title', sa.String(255), nullable=True),
        sa.Column('role_type', sa.String(20), default='unknown', nullable=False),
        sa.Column('role_confidence', sa.Float(), default=0.0),
        sa.Column('topic_tags', postgresql.ARRAY(sa.String()), default=[]),
        sa.Column('research_interests', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('works_count', sa.Integer(), default=0),
        sa.Column('cited_by_count', sa.Integer(), default=0),
        sa.Column('h_index', sa.Integer(), default=0),
        sa.Column('latest_active_year', sa.Integer(), nullable=True),
        sa.Column('visibility_status', sa.String(20), default='active', nullable=False),
        sa.Column('is_visible', sa.Boolean(), default=True, nullable=False),
        sa.Column('unified_person_id', sa.String(100), nullable=True),
        sa.Column('department_name', sa.String(255), nullable=True),
        sa.Column('lab_name', sa.String(255), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_talent_name', 'core_talent', ['name'])
    op.create_index('ix_core_talent_school_id', 'core_talent', ['school_id'])
    op.create_index('ix_core_talent_source_record_id', 'core_talent', ['source_record_id'])
    op.create_index('ix_core_talent_role_type', 'core_talent', ['role_type'])
    op.create_index('ix_core_talent_orcid', 'core_talent', ['orcid'])
    op.create_index('ix_core_talent_school_role', 'core_talent', ['school_id', 'role_type', 'is_visible'])

    # ============================================
    # core_role_profile table
    # ============================================
    op.create_table(
        'core_role_profile',
        sa.Column('profile_id', sa.Integer(), primary_key=True),
        sa.Column('talent_id', sa.Integer(), sa.ForeignKey('core_talent.talent_id'), unique=True, nullable=False),
        sa.Column('role_type', sa.String(20), default='unknown', nullable=False),
        sa.Column('role_confidence', sa.Float(), default=0.0),
        sa.Column('role_reason', sa.Text(), nullable=True),
        sa.Column('identification_method', sa.String(50), nullable=True),
        sa.Column('identified_at', sa.String(50), nullable=True),
        sa.Column('position_title', sa.String(255), nullable=True),
        sa.Column('academic_age', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_role_profile_talent_id', 'core_role_profile', ['talent_id'])

    # ============================================
    # core_selected_work table
    # ============================================
    op.create_table(
        'core_selected_work',
        sa.Column('work_id', sa.Integer(), primary_key=True),
        sa.Column('talent_id', sa.Integer(), sa.ForeignKey('core_talent.talent_id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('venue_name', sa.String(255), nullable=True),
        sa.Column('citation_count', sa.Integer(), default=0),
        sa.Column('source_work_id', sa.String(100), nullable=True),
        sa.Column('doi', sa.String(100), nullable=True),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_core_selected_work_talent_id', 'core_selected_work', ['talent_id'])

    # ============================================
    # stat_overview_snapshot table
    # ============================================
    op.create_table(
        'stat_overview_snapshot',
        sa.Column('snapshot_id', sa.Integer(), primary_key=True),
        sa.Column('stat_version', sa.String(50), nullable=False),
        sa.Column('generated_at', sa.String(50), nullable=False),
        sa.Column('school_count', sa.Integer(), default=0),
        sa.Column('professor_count', sa.Integer(), default=0),
        sa.Column('student_count', sa.Integer(), default=0),
        sa.Column('talent_count', sa.Integer(), default=0),
        sa.Column('generated_by_batch_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Integer(), default=1),
    )
    op.create_index('ix_stat_overview_version', 'stat_overview_snapshot', ['stat_version'])

    # ============================================
    # stat_school_snapshot table
    # ============================================
    op.create_table(
        'stat_school_snapshot',
        sa.Column('snapshot_id', sa.Integer(), primary_key=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('core_school.school_id'), nullable=False),
        sa.Column('stat_version', sa.String(50), nullable=False),
        sa.Column('generated_at', sa.String(50), nullable=False),
        sa.Column('professor_count', sa.Integer(), default=0),
        sa.Column('student_count', sa.Integer(), default=0),
        sa.Column('talent_count', sa.Integer(), default=0),
        sa.Column('graduate_count', sa.Integer(), default=0),
        sa.Column('unknown_count', sa.Integer(), default=0),
        sa.Column('generated_by_batch_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Integer(), default=1),
    )
    op.create_index('ix_stat_school_snapshot_school_id', 'stat_school_snapshot', ['school_id'])
    op.create_index('ix_stat_school_snapshot_version', 'stat_school_snapshot', ['stat_version'])

    # ============================================
    # iam_user_account table
    # ============================================
    op.create_table(
        'iam_user_account',
        sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role_type', sa.String(20), default='user', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_ip', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_iam_user_username', 'iam_user_account', ['username'])
    op.create_index('ix_iam_user_email', 'iam_user_account', ['email'])

    # ============================================
    # iam_user_school_scope table
    # ============================================
    op.create_table(
        'iam_user_school_scope',
        sa.Column('scope_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=False),
        sa.Column('scope_type', sa.String(20), nullable=False),
        sa.Column('scope_value', sa.String(100), nullable=True),
        sa.Column('granted_by', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_iam_scope_user_id', 'iam_user_school_scope', ['user_id'])
    op.create_index('ix_iam_scope_type_value', 'iam_user_school_scope', ['scope_type', 'scope_value'])
    op.create_unique_constraint('uq_user_scope', 'iam_user_school_scope', ['user_id', 'scope_type', 'scope_value'])

    # ============================================
    # sync_batch table
    # ============================================
    op.create_table(
        'sync_batch',
        sa.Column('batch_id', sa.Integer(), primary_key=True),
        sa.Column('batch_code', sa.String(50), unique=True, nullable=False),
        sa.Column('batch_type', sa.String(20), nullable=False),
        sa.Column('source_type', sa.String(50), default='openalex'),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_records', sa.Integer(), default=0),
        sa.Column('success_records', sa.Integer(), default=0),
        sa.Column('failed_records', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', sa.String(50), default='system'),
        sa.Column('config_snapshot', postgresql.JSONB(), nullable=True),
    )
    op.create_index('ix_sync_batch_code', 'sync_batch', ['batch_code'])
    op.create_index('ix_sync_batch_status', 'sync_batch', ['status'])

    # ============================================
    # raw_source_record table
    # ============================================
    op.create_table(
        'raw_source_record',
        sa.Column('record_id', sa.Integer(), primary_key=True),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(), nullable=False),
        sa.Column('processed_status', sa.String(20), default='pending'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_info', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_raw_record_batch_id', 'raw_source_record', ['batch_id'])
    op.create_index('ix_raw_record_source', 'raw_source_record', ['source_type', 'source_id'])
    op.create_index('ix_raw_record_status', 'raw_source_record', ['processed_status'])

    # ============================================
    # search_talent_document table
    # ============================================
    op.create_table(
        'search_talent_document',
        sa.Column('document_id', sa.Integer(), primary_key=True),
        sa.Column('talent_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('school_name', sa.String(255), nullable=True),
        sa.Column('country_code', sa.String(10), nullable=True),
        sa.Column('search_text', sa.Text(), nullable=False),
        sa.Column('role_type', sa.String(20), nullable=False),
        sa.Column('topic_tags', postgresql.ARRAY(sa.String()), default=[]),
        sa.Column('works_count', sa.Integer(), default=0),
        sa.Column('cited_by_count', sa.Integer(), default=0),
        sa.Column('h_index', sa.Integer(), default=0),
        sa.Column('latest_active_year', sa.Integer(), nullable=True),
        sa.Column('orcid', sa.String(50), nullable=True),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
    )
    op.create_index('ix_search_talent_id', 'search_talent_document', ['talent_id'])
    op.create_index('ix_search_school_id', 'search_talent_document', ['school_id'])
    op.create_index('ix_search_country_code', 'search_talent_document', ['country_code'])
    op.create_index('ix_search_role_type', 'search_talent_document', ['role_type'])
    op.create_index('ix_search_active', 'search_talent_document', ['is_active'])
    # Full-text search index on search_text
    op.execute("CREATE INDEX ix_search_text ON search_talent_document USING gin(to_tsvector('simple', search_text))")

    # ============================================
    # audit_operation_log table
    # ============================================
    op.create_table(
        'audit_operation_log',
        sa.Column('log_id', sa.Integer(), primary_key=True),
        sa.Column('event_time', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_ip', sa.String(50), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_subtype', sa.String(50), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('operation_detail', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
    )
    op.create_index('ix_audit_event_time', 'audit_operation_log', ['event_time'])
    op.create_index('ix_audit_user_event', 'audit_operation_log', ['user_id', 'event_time'])
    op.create_index('ix_audit_event_type', 'audit_operation_log', ['event_type', 'event_time'])
    op.create_index('ix_audit_resource', 'audit_operation_log', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_request_id', 'audit_operation_log', ['request_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_operation_log')
    op.drop_table('search_talent_document')
    op.drop_table('raw_source_record')
    op.drop_table('sync_batch')
    op.drop_table('iam_user_school_scope')
    op.drop_table('iam_user_account')
    op.drop_table('stat_school_snapshot')
    op.drop_table('stat_overview_snapshot')
    op.drop_table('core_selected_work')
    op.drop_table('core_role_profile')
    op.drop_table('core_talent')
    op.drop_table('core_school_alias')
    op.drop_table('core_school')
    op.drop_table('core_country')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS sync_job_status_enum')
    op.execute('DROP TYPE IF EXISTS user_role_type_enum')
    op.execute('DROP TYPE IF EXISTS visibility_status_enum')
    op.execute('DROP TYPE IF EXISTS role_type_enum')

    # Drop extensions (optional, comment out if you want to keep them)
    # op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
