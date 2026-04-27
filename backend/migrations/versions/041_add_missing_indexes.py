"""Add missing indexes for raw data layer

Revision ID: 041
Revises: 040_add_venue_snapshot
Create Date: 2026-04-27

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Indexes for raw_work to support task-scoped queries and sub-task lookups
    op.create_index(
        'ix_raw_work_fetch_task_id',
        'raw_work',
        ['fetch_task_id'],
        unique=False
    )
    op.create_index(
        'ix_raw_work_sub_task_id',
        'raw_work',
        ['sub_task_id'],
        unique=False
    )

    # Index for raw_author to support task-scoped queries
    op.create_index(
        'ix_raw_author_fetch_task_id',
        'raw_author',
        ['fetch_task_id'],
        unique=False
    )

    # Indexes for rel_author_tech_belong to support venue-based and task-based lookups
    op.create_index(
        'ix_rel_author_tech_belong_source_venue_id',
        'rel_author_tech_belong',
        ['source_venue_id'],
        unique=False
    )
    op.create_index(
        'ix_rel_author_tech_belong_source_task_id',
        'rel_author_tech_belong',
        ['source_task_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_rel_author_tech_belong_source_task_id', table_name='rel_author_tech_belong')
    op.drop_index('ix_rel_author_tech_belong_source_venue_id', table_name='rel_author_tech_belong')
    op.drop_index('ix_raw_author_fetch_task_id', table_name='raw_author')
    op.drop_index('ix_raw_work_sub_task_id', table_name='raw_work')
    op.drop_index('ix_raw_work_fetch_task_id', table_name='raw_work')
