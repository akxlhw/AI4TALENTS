"""add_lab_talent_photo

Revision ID: 051_add_lab_talent_photo
Revises: 050_add_lab_talent_table
Create Date: 2026-07-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '051_add_lab_talent_photo'
down_revision: Union[str, None] = '050_add_lab_talent_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # photo_url: person photo URL (crawler output field)
    op.add_column('lab_talent', sa.Column('photo_url', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('lab_talent', 'photo_url')
