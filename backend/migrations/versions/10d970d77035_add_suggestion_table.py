"""add suggestion table

Revision ID: 10d970d77035
Revises: f8e297abd879
Create Date: 2026-05-27 11:43:56.578320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10d970d77035'
down_revision: Union[str, None] = 'f8e297abd879'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'shared_suggestion',
        sa.Column('suggestion_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('admin_reply', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['iam_user_account.user_id']),
        sa.PrimaryKeyConstraint('suggestion_id'),
    )
    op.create_index(op.f('ix_shared_suggestion_suggestion_id'), 'shared_suggestion', ['suggestion_id'], unique=False)
    op.create_index(op.f('ix_shared_suggestion_user_id'), 'shared_suggestion', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_shared_suggestion_user_id'), table_name='shared_suggestion')
    op.drop_index(op.f('ix_shared_suggestion_suggestion_id'), table_name='shared_suggestion')
    op.drop_table('shared_suggestion')
