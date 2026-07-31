"""Add search indexes for os_developer

Revision ID: 056
Revises: 055_add_lab_advisor_fields
Create Date: 2026-07-31

This migration improves open-source developer search performance:
1. Enables pg_trgm extension (idempotent)
2. Adds GIN trigram indexes on name/github_login/company/location/bio
   to accelerate ILIKE keyword search
3. Converts tech_tags and primary_languages from JSON to JSONB
   and adds GIN indexes for containment/existence queries
"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '056'
down_revision = '055_add_lab_advisor_fields'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the database is PostgreSQL."""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Add trigram and JSONB GIN indexes for os_developer search."""
    if not _is_postgres():
        return

    # Enable pg_trgm extension for trigram similarity (idempotent)
    op.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))

    # Convert JSON columns to JSONB for indexable containment queries
    op.execute(text('''
        ALTER TABLE os_developer
        ALTER COLUMN tech_tags TYPE jsonb USING tech_tags::jsonb
    '''))
    op.execute(text('''
        ALTER TABLE os_developer
        ALTER COLUMN primary_languages TYPE jsonb USING primary_languages::jsonb
    '''))

    # GIN trigram indexes for ILIKE keyword search
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_name_trgm
        ON os_developer USING GIN(name gin_trgm_ops)
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_github_login_trgm
        ON os_developer USING GIN(github_login gin_trgm_ops)
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_company_trgm
        ON os_developer USING GIN(company gin_trgm_ops)
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_location_trgm
        ON os_developer USING GIN(location gin_trgm_ops)
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_bio_trgm
        ON os_developer USING GIN(bio gin_trgm_ops)
    '''))

    # GIN indexes on JSONB columns for @> and ?| operators
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_tech_tags_gin
        ON os_developer USING GIN(tech_tags)
    '''))
    op.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_os_developer_primary_languages_gin
        ON os_developer USING GIN(primary_languages)
    '''))


def downgrade() -> None:
    """Remove os_developer search indexes and revert JSONB columns to JSON."""
    if not _is_postgres():
        return

    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_primary_languages_gin'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_tech_tags_gin'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_bio_trgm'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_location_trgm'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_company_trgm'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_github_login_trgm'))
    op.execute(text('DROP INDEX IF EXISTS ix_os_developer_name_trgm'))

    op.execute(text('''
        ALTER TABLE os_developer
        ALTER COLUMN tech_tags TYPE json USING tech_tags::json
    '''))
    op.execute(text('''
        ALTER TABLE os_developer
        ALTER COLUMN primary_languages TYPE json USING primary_languages::json
    '''))
