"""Add talent_pool tables

Revision ID: 005_add_talent_pool
Revises: 004_add_tech_element
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_talent_pool'
down_revision: Union[str, None] = '004_add_tech_element'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add followup_status column to iam_favorite_talent
    op.add_column('iam_favorite_talent', sa.Column('followup_status', sa.String(30), default='new_found', nullable=False))

    # Create iam_talent_pool table
    op.create_table(
        'iam_talent_pool',
        sa.Column('pool_id', sa.Integer(), primary_key=True),
        sa.Column('pool_name', sa.String(100), nullable=False),
        sa.Column('pool_type', sa.String(30), default='custom', nullable=False),
        sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('iam_user_account.user_id'), nullable=False),
        sa.Column('scope_desc', sa.Text(), nullable=True),
        sa.Column('pool_status', sa.String(20), default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for talent_pool
    op.create_index('ix_talent_pool_owner', 'iam_talent_pool', ['owner_user_id'])
    op.create_index('ix_talent_pool_status', 'iam_talent_pool', ['pool_status'])

    # Create iam_talent_pool_member table
    op.create_table(
        'iam_talent_pool_member',
        sa.Column('member_id', sa.Integer(), primary_key=True),
        sa.Column('pool_id', sa.Integer(), sa.ForeignKey('iam_talent_pool.pool_id'), nullable=False),
        sa.Column('talent_id', sa.Integer(), sa.ForeignKey('core_talent.talent_id'), nullable=False),
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('pool_id', 'talent_id', name='uq_pool_talent'),
    )

    # Create indexes for talent_pool_member
    op.create_index('ix_pool_member_pool', 'iam_talent_pool_member', ['pool_id'])
    op.create_index('ix_pool_member_talent', 'iam_talent_pool_member', ['talent_id'])


def downgrade() -> None:
    op.drop_table('iam_talent_pool_member')
    op.drop_table('iam_talent_pool')
    op.drop_column('iam_favorite_talent', 'followup_status')
