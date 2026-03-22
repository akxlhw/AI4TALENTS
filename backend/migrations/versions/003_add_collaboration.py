"""Add collaboration and work_author tables

Revision ID: 003_add_collaboration
Revises: 002_add_favorite_talent
Create Date: 2026-03-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_collaboration'
down_revision: Union[str, None] = '002_add_favorite_talent'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create work_author table (without foreign key for SQLite compatibility)
    op.create_table(
        'core_work_author',
        sa.Column('work_author_id', sa.Integer(), nullable=False),
        sa.Column('source_work_id', sa.String(100), nullable=False),
        sa.Column('work_title', sa.String(500), nullable=True),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('talent_id', sa.Integer(), nullable=True),
        sa.Column('author_position', sa.Integer(), nullable=True),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('work_author_id')
    )
    with op.batch_alter_table('core_work_author') as batch_op:
        batch_op.create_index('ix_core_work_author_id', ['work_author_id'])
        batch_op.create_index('ix_core_work_author_source_work_id', ['source_work_id'])
        batch_op.create_index('ix_core_work_author_talent_id', ['talent_id'])

    # Create collaboration table (without foreign key for SQLite compatibility)
    op.create_table(
        'core_collaboration',
        sa.Column('collaboration_id', sa.Integer(), nullable=False),
        sa.Column('talent_id_1', sa.Integer(), nullable=False),
        sa.Column('talent_id_2', sa.Integer(), nullable=False),
        sa.Column('collaboration_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('first_collaboration_year', sa.Integer(), nullable=True),
        sa.Column('last_collaboration_year', sa.Integer(), nullable=True),
        sa.Column('source_batch_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('collaboration_id'),
        sa.UniqueConstraint('talent_id_1', 'talent_id_2', name='uq_collaboration_pair')
    )
    with op.batch_alter_table('core_collaboration') as batch_op:
        batch_op.create_index('ix_core_collaboration_id', ['collaboration_id'])
        batch_op.create_index('ix_core_collaboration_talent_id_1', ['talent_id_1'])
        batch_op.create_index('ix_core_collaboration_talent_id_2', ['talent_id_2'])


def downgrade() -> None:
    op.drop_table('core_collaboration')
    op.drop_table('core_work_author')
