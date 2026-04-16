"""Fix JD match tables missing updated_at column

Revision ID: 030
Revises: 029
Create Date: 2026-04-16

This migration adds missing updated_at columns to jd_match_session
and jd_match_result tables.
"""
from alembic import op
from sqlalchemy import Column, DateTime


# revision identifiers, used by Alembic.
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing updated_at columns."""
    # Add updated_at to jd_match_session
    op.add_column(
        'jd_match_session',
        Column('updated_at', DateTime, nullable=True)
    )

    # Add updated_at to jd_match_result
    op.add_column(
        'jd_match_result',
        Column('updated_at', DateTime, nullable=True)
    )


def downgrade() -> None:
    """Remove updated_at columns."""
    op.drop_column('jd_match_result', 'updated_at')
    op.drop_column('jd_match_session', 'updated_at')
