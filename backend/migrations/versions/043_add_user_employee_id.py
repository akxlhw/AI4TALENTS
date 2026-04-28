"""Add employee_id to user account

Revision ID: 043
Revises: 042_fix_author_tech_belong_unique
Create Date: 2026-04-28

This migration:
1. Adds employee_id column to iam_user_account for enterprise identity verification
2. Creates unique index on employee_id
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add employee_id column
    op.add_column(
        'iam_user_account',
        sa.Column('employee_id', sa.String(20), nullable=True)
    )
    # Create unique index
    op.create_index(
        'ix_user_account_employee_id',
        'iam_user_account',
        ['employee_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_user_account_employee_id', table_name='iam_user_account')
    op.drop_column('iam_user_account', 'employee_id')
