"""add lab_logo_url to lab_talent

Revision ID: 95980baaa3eb
Revises: 051_add_lab_talent_photo
Create Date: 2026-07-12 20:37:29.655214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95980baaa3eb'
down_revision: Union[str, None] = '051_add_lab_talent_photo'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_talent', sa.Column('lab_logo_url', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('lab_talent', 'lab_logo_url')
