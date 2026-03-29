"""Add data version, publish, correction and quality models

Revision ID: 008_add_data_version
Revises: 007_add_collect_config
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_add_data_version'
down_revision: Union[str, None] = '007_add_collect_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create data_version table
    op.create_table(
        'data_version',
        sa.Column('version_id', sa.Integer(), primary_key=True),
        sa.Column('version_code', sa.String(50), unique=True, nullable=False),
        sa.Column('version_name', sa.String(100), nullable=False),
        sa.Column('version_type', sa.String(20), default='snapshot', nullable=False),
        sa.Column('base_version_id', sa.Integer(), sa.ForeignKey('data_version.version_id'), nullable=True),
        sa.Column('source_task_id', sa.Integer(), sa.ForeignKey('sync_collect_task.task_id'), nullable=True),
        sa.Column('total_talents', sa.Integer(), default=0),
        sa.Column('total_schools', sa.Integer(), default=0),
        sa.Column('total_works', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_published', sa.Boolean(), default=False, nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('published_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_data_version_code', 'data_version', ['version_code'])
    op.create_index('ix_data_version_active', 'data_version', ['is_active'])

    # Create data_publish_record table
    op.create_table(
        'data_publish_record',
        sa.Column('publish_id', sa.Integer(), primary_key=True),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('data_version.version_id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('previous_version_id', sa.Integer(), sa.ForeignKey('data_version.version_id'), nullable=True),
        sa.Column('operated_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=False),
        sa.Column('operated_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_publish_record_version', 'data_publish_record', ['version_id'])

    # Create data_correction_record table
    op.create_table(
        'data_correction_record',
        sa.Column('correction_id', sa.Integer(), primary_key=True),
        sa.Column('target_type', sa.String(30), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(50), nullable=False),
        sa.Column('original_value', sa.Text(), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('correction_type', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('corrected_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=False),
        sa.Column('status', sa.String(20), default='applied', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_correction_target', 'data_correction_record', ['target_type', 'target_id'])
    op.create_index('ix_correction_status', 'data_correction_record', ['status'])

    # Create data_quality_summary table
    op.create_table(
        'data_quality_summary',
        sa.Column('summary_id', sa.Integer(), primary_key=True),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('data_version.version_id'), nullable=False),
        sa.Column('summary_date', sa.DateTime(), nullable=False),
        sa.Column('talent_total', sa.Integer(), default=0),
        sa.Column('talent_with_orcid', sa.Integer(), default=0),
        sa.Column('talent_with_affiliation', sa.Integer(), default=0),
        sa.Column('talent_with_works', sa.Integer(), default=0),
        sa.Column('talent_completeness_avg', sa.Integer(), default=0),
        sa.Column('school_total', sa.Integer(), default=0),
        sa.Column('school_with_ror', sa.Integer(), default=0),
        sa.Column('school_with_country', sa.Integer(), default=0),
        sa.Column('work_total', sa.Integer(), default=0),
        sa.Column('work_with_doi', sa.Integer(), default=0),
        sa.Column('tech_tag_total', sa.Integer(), default=0),
        sa.Column('tech_tag_confirmed', sa.Integer(), default=0),
        sa.Column('tech_tag_auto_identified', sa.Integer(), default=0),
        sa.Column('tech_tag_pending_confirm', sa.Integer(), default=0),
        sa.Column('issues_critical', sa.Integer(), default=0),
        sa.Column('issues_warning', sa.Integer(), default=0),
        sa.Column('issues_info', sa.Integer(), default=0),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_quality_summary_version', 'data_quality_summary', ['version_id'])
    op.create_index('ix_quality_summary_date', 'data_quality_summary', ['summary_date'])


def downgrade() -> None:
    op.drop_table('data_quality_summary')
    op.drop_table('data_correction_record')
    op.drop_table('data_publish_record')
    op.drop_table('data_version')
