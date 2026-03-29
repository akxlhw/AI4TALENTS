"""Add default_view to user and extend scope_type

Revision ID: 006_add_default_view
Revises: 005_add_talent_pool
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_default_view'
down_revision: Union[str, None] = '005_add_talent_pool'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add default_view column to iam_user_account
    op.add_column(
        'iam_user_account',
        sa.Column('default_view', sa.String(30), default='tech_element', nullable=False, server_default='tech_element')
    )


def downgrade() -> None:
    op.drop_column('iam_user_account', 'default_view')
