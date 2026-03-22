"""Add favorite_talent table

Revision ID: 002_add_favorite_talent
Revises: 001_initial
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_favorite_talent'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create iam_favorite_talent table with unique constraint in table definition
    op.create_table(
        'iam_favorite_talent',
        sa.Column('favorite_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=False),
        sa.Column('talent_id', sa.Integer(), sa.ForeignKey('core_talent.talent_id'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'talent_id', name='uq_user_favorite_talent'),
    )

    # Create indexes
    op.create_index('ix_iam_favorite_user_id', 'iam_favorite_talent', ['user_id'])
    op.create_index('ix_iam_favorite_talent_id', 'iam_favorite_talent', ['talent_id'])
    op.create_index('ix_iam_favorite_is_active', 'iam_favorite_talent', ['is_active'])


def downgrade() -> None:
    op.drop_table('iam_favorite_talent')
