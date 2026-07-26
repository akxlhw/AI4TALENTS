"""add_lab_advisor_fields

Revision ID: 055_add_lab_advisor_fields
Revises: 9d176b3c88e8
Create Date: 2026-07-25 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '055_add_lab_advisor_fields'
down_revision: Union[str, None] = '9d176b3c88e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_talent', sa.Column('advisor', sa.String(length=255), nullable=True))
    op.add_column('lab_talent', sa.Column('co_advisor', sa.String(length=255), nullable=True))
    # Index for reverse lookup (find students by advisor name)
    op.create_index('ix_lab_talent_advisor', 'lab_talent', ['advisor'])


def downgrade() -> None:
    op.drop_index('ix_lab_talent_advisor', table_name='lab_talent')
    op.drop_column('lab_talent', 'co_advisor')
    op.drop_column('lab_talent', 'advisor')
