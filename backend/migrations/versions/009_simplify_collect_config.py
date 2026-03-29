"""Simplify collect config for MVP v1.1

Revision ID: 009
Revises: 008_add_data_version
Create Date: 2024-03-24

Changes:
1. Add collect_sources and last_collect_at to core_tech_element
2. Simplify sync_collect_task: add tech_element_id, collect_mode; remove strategy_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON

# revision identifiers
revision = '009_simplify_collect_config'
down_revision = '008_add_data_version'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to core_tech_element
    op.add_column('core_tech_element', sa.Column('collect_sources', JSON, nullable=True))
    op.add_column('core_tech_element', sa.Column('last_collect_at', sa.DateTime, nullable=True))

    # Add columns to sync_collect_task
    op.add_column('sync_collect_task', sa.Column('tech_element_id', sa.Integer, nullable=True))
    op.add_column('sync_collect_task', sa.Column('collect_mode', sa.String(20), nullable=True, server_default='full'))

    # Add foreign key
    op.create_foreign_key(
        'fk_collect_task_tech_element',
        'sync_collect_task',
        'core_tech_element',
        ['tech_element_id'],
        ['tech_element_id']
    )

    # Create index
    op.create_index('ix_sync_collect_task_tech_element_id', 'sync_collect_task', ['tech_element_id'])


def downgrade():
    op.drop_index('ix_sync_collect_task_tech_element_id', 'sync_collect_task')
    op.drop_constraint('fk_collect_task_tech_element', 'sync_collect_task', type_='foreignkey')
    op.drop_column('sync_collect_task', 'collect_mode')
    op.drop_column('sync_collect_task', 'tech_element_id')
    op.drop_column('core_tech_element', 'last_collect_at')
    op.drop_column('core_tech_element', 'collect_sources')
