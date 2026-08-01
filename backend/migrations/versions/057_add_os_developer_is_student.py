"""Add is_student column to os_developer

Revision ID: 057
Revises: 056
Create Date: 2026-08-01

Adds a student flag to open-source developers:
1. is_student BOOLEAN NOT NULL DEFAULT FALSE
2. B-tree index on is_student for filter queries
"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '057'
down_revision = '056'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the database is PostgreSQL."""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Add is_student column with default false and a btree index."""
    if not _is_postgres():
        return

    op.execute(text('''
        ALTER TABLE os_developer
        ADD COLUMN IF NOT EXISTS is_student BOOLEAN NOT NULL DEFAULT FALSE
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_is_student
        ON os_developer (is_student)
    '''))


def downgrade() -> None:
    """Drop is_student column and its index."""
    if not _is_postgres():
        return

    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_is_student'))
    op.execute(text('ALTER TABLE os_developer DROP COLUMN IF EXISTS is_student'))
