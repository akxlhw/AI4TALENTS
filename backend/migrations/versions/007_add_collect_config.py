"""Add collect scope, strategy and task models

Revision ID: 007_add_collect_config
Revises: 006_add_default_view
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_collect_config'
down_revision: Union[str, None] = '006_add_default_view'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sync_collect_scope table
    op.create_table(
        'sync_collect_scope',
        sa.Column('scope_id', sa.Integer(), primary_key=True),
        sa.Column('scope_code', sa.String(50), unique=True, nullable=False),
        sa.Column('scope_name', sa.String(100), nullable=False),
        sa.Column('scope_type', sa.String(30), nullable=False),
        sa.Column('scope_value', sa.JSON(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_collect_scope_code', 'sync_collect_scope', ['scope_code'])
    op.create_index('ix_collect_scope_type', 'sync_collect_scope', ['scope_type'])

    # Create sync_collect_strategy table
    op.create_table(
        'sync_collect_strategy',
        sa.Column('strategy_id', sa.Integer(), primary_key=True),
        sa.Column('strategy_code', sa.String(50), unique=True, nullable=False),
        sa.Column('strategy_name', sa.String(100), nullable=False),
        sa.Column('strategy_type', sa.String(30), default='scheduled', nullable=False),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('scope_ids', sa.JSON(), nullable=True),
        sa.Column('data_types', sa.JSON(), nullable=False),
        sa.Column('fetch_config', sa.JSON(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_collect_strategy_code', 'sync_collect_strategy', ['strategy_code'])
    op.create_index('ix_collect_strategy_type', 'sync_collect_strategy', ['strategy_type'])

    # Create sync_collect_task table
    op.create_table(
        'sync_collect_task',
        sa.Column('task_id', sa.Integer(), primary_key=True),
        sa.Column('task_code', sa.String(50), unique=True, nullable=False),
        sa.Column('strategy_id', sa.Integer(), sa.ForeignKey('sync_collect_strategy.strategy_id'), nullable=True),
        sa.Column('task_type', sa.String(30), nullable=False),
        sa.Column('triggered_by', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('progress_percent', sa.Integer(), default=0),
        sa.Column('current_step', sa.String(100), nullable=True),
        sa.Column('total_records', sa.Integer(), default=0),
        sa.Column('processed_records', sa.Integer(), default=0),
        sa.Column('success_records', sa.Integer(), default=0),
        sa.Column('failed_records', sa.Integer(), default=0),
        sa.Column('skipped_records', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('result_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_collect_task_code', 'sync_collect_task', ['task_code'])
    op.create_index('ix_collect_task_status', 'sync_collect_task', ['status'])
    op.create_index('ix_collect_task_strategy', 'sync_collect_task', ['strategy_id'])


def downgrade() -> None:
    op.drop_table('sync_collect_task')
    op.drop_table('sync_collect_strategy')
    op.drop_table('sync_collect_scope')
