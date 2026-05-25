"""add privacy consent fields to user account

Revision ID: f8e297abd879
Revises: 99aed1b1b7e7
Create Date: 2026-05-25 19:05:50.565250

This migration adds privacy policy and terms of use acceptance tracking
to the user account table, supporting PIPL/GDPR compliance requirements.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e297abd879'
down_revision: Union[str, None] = '99aed1b1b7e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add privacy policy acceptance fields
    op.add_column(
        'iam_user_account',
        sa.Column('privacy_policy_accepted_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'iam_user_account',
        sa.Column('privacy_policy_version', sa.String(length=20), nullable=True)
    )

    # Add terms of use acceptance fields
    op.add_column(
        'iam_user_account',
        sa.Column('terms_of_use_accepted_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'iam_user_account',
        sa.Column('terms_of_use_version', sa.String(length=20), nullable=True)
    )

    # Add storage consent level field
    op.add_column(
        'iam_user_account',
        sa.Column(
            'storage_consent_level',
            sa.String(length=20),
            server_default='necessary',
            nullable=False,
        )
    )


def downgrade() -> None:
    op.drop_column('iam_user_account', 'storage_consent_level')
    op.drop_column('iam_user_account', 'terms_of_use_version')
    op.drop_column('iam_user_account', 'terms_of_use_accepted_at')
    op.drop_column('iam_user_account', 'privacy_policy_version')
    op.drop_column('iam_user_account', 'privacy_policy_accepted_at')
