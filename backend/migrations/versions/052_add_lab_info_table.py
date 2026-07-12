"""add_lab_info_table

Revision ID: 052_add_lab_info_table
Revises: 051_add_lab_talent_photo
Create Date: 2026-07-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '052_add_lab_info_table'
down_revision: Union[str, None] = '95980baaa3eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_info',
        sa.Column('lab_info_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('parent_lab', sa.String(length=255), nullable=False),
        sa.Column('lab_slug', sa.String(length=100), nullable=True),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('research_focus', sa.String(length=1000), nullable=True),
        sa.Column('research_directions', sa.JSON(), nullable=True),
        sa.Column('homepage', sa.String(length=500), nullable=True),
        sa.Column('logo_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('lab_info_id'),
        sa.UniqueConstraint('parent_lab', name='uq_lab_info_parent_lab'),
    )
    op.create_index('ix_lab_info_lab_info_id', 'lab_info', ['lab_info_id'])
    op.create_index('ix_lab_info_parent_lab', 'lab_info', ['parent_lab'], unique=True)
    op.create_index('ix_lab_info_lab_slug', 'lab_info', ['lab_slug'])


def downgrade() -> None:
    op.drop_index('ix_lab_info_lab_slug', table_name='lab_info')
    op.drop_index('ix_lab_info_parent_lab', table_name='lab_info')
    op.drop_index('ix_lab_info_lab_info_id', table_name='lab_info')
    op.drop_table('lab_info')
