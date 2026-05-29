"""add created_at index to user account

Revision ID: 1c4fcce9cd43
Revises: 10d970d77035
Create Date: 2026-05-29 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c4fcce9cd43'
down_revision: Union[str, None] = '10d970d77035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f('ix_iam_user_account_created_at'),
        'iam_user_account',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_iam_user_account_created_at'),
        table_name='iam_user_account',
    )
