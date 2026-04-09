"""fix schema issues from removed migration

Revision ID: 024
Revises: 023
Create Date: 2026-04-09

This migration restores the correct schema changes that were lost when
the erroneous migration 7850ff4764a7 was deleted.

Fixes:
1. Add unique index for source_record_id (required for ON CONFLICT)
2. Fix topic_tags column type (ARRAY -> JSON)

Note: ON CONFLICT requires a regular unique index, NOT a partial index.
"""
from alembic import op


revision: str = '024'
down_revision: str = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix schema issues."""

    # 1. Add unique indexes for source_record_id
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_core_school_source_record_id_unique
        ON core_school (source_record_id)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_core_talent_source_record_id_unique
        ON core_talent (source_record_id)
    """)

    # 2. Fix core_talent.topic_tags type: ARRAY -> JSON
    op.execute("""
        ALTER TABLE core_talent
        ALTER COLUMN topic_tags TYPE JSON
        USING CASE
            WHEN topic_tags IS NULL THEN '[]'::json
            ELSE to_json(topic_tags)::json
        END
    """)


def downgrade() -> None:
    """Revert schema fixes."""
    # Revert topic_tags type
    op.execute("""
        ALTER TABLE core_talent
        ALTER COLUMN topic_tags TYPE VARCHAR[]
        USING CASE
            WHEN topic_tags::text = '[]' THEN '{}'
            ELSE ARRAY(SELECT json_array_elements_text(topic_tags))
        END
    """)

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_core_talent_source_record_id_unique")
    op.execute("DROP INDEX IF EXISTS ix_core_school_source_record_id_unique")
