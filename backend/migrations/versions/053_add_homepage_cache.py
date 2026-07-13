"""add_homepage_cache

Revision ID: 053_add_homepage_cache
Revises: 052_add_lab_info_table
Create Date: 2026-07-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '053_add_homepage_cache'
down_revision: Union[str, None] = '052_add_lab_info_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_talent', sa.Column('homepage_cache', sa.Text(), nullable=True))
    op.add_column('lab_talent', sa.Column('homepage_cached_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('lab_talent', 'homepage_cached_at')
    op.drop_column('lab_talent', 'homepage_cache')
