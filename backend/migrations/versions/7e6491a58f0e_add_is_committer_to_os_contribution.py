"""add_is_committer_to_os_contribution

Revision ID: 7e6491a58f0e
Revises: 048
Create Date: 2026-05-07 22:14:09.100748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7e6491a58f0e'
down_revision: Union[str, None] = '048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'os_contribution',
        sa.Column('is_committer', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('os_contribution', 'is_committer')
