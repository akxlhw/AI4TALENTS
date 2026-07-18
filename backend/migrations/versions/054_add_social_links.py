"""add_social_links

Revision ID: 054_add_social_links
Revises: 053_add_homepage_cache
Create Date: 2026-07-17 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '054_add_social_links'
down_revision: Union[str, None] = '053_add_homepage_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_talent', sa.Column('social_links', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('lab_talent', 'social_links')
