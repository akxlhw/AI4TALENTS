"""Add GIN indexes for JD match and search optimization

Revision ID: 031
Revises: 030
Create Date: 2026-04-16

This migration adds GIN indexes to optimize:
1. openalex_topics JSON array precise match (for JD matching with exact topic names)
2. openalex_topics text fuzzy search (for talent keyword search)
3. raw_work.title text search (for paper title search in JD matching)
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GIN indexes for search optimization."""

    # Enable pg_trgm extension if not exists (required for trigram indexes)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 1. JSON array precise match index for openalex_topics (JD matching)
    # Uses jsonb_path_ops for efficient containment queries (@> operator)
    # Example: openalex_topics::jsonb @> '["Machine Learning"]'::jsonb
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_core_talent_openalex_topics_gin
        ON core_talent USING GIN ((openalex_topics::jsonb) jsonb_path_ops)
        WHERE openalex_topics IS NOT NULL
    """)

    # 2. Trigram index for openalex_topics fuzzy search (talent keyword search)
    # Uses gin_trgm_ops for ILIKE and similarity queries on the text representation
    # Example: openalex_topics::text ILIKE '%Machine Learning%'
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_core_talent_openalex_topics_trgm
        ON core_talent USING GIN ((openalex_topics::text) gin_trgm_ops)
        WHERE openalex_topics IS NOT NULL
    """)

    # 3. Trigram index for paper title fuzzy search (JD matching)
    # Uses gin_trgm_ops for ILIKE and similarity queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_raw_work_title_trgm
        ON raw_work USING GIN (title gin_trgm_ops)
        WHERE title IS NOT NULL
    """)


def downgrade() -> None:
    """Remove GIN indexes."""
    op.execute("DROP INDEX IF EXISTS ix_raw_work_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_core_talent_openalex_topics_trgm")
    op.execute("DROP INDEX IF EXISTS ix_core_talent_openalex_topics_gin")
    # Note: We don't drop pg_trgm extension as it might be used by other indexes
