"""Update search_text to include openalex_topics for fulltext search

Revision ID: 045
Revises: 044_add_stats_research_topic
Create Date: 2026-04-29

This migration:
1. Updates existing search_talent_document records to include openalex_topics in search_text
2. Ensures research topic keywords can be matched by fulltext/hybrid search modes
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update search_text to include openalex_topics for existing documents
    # Note: openalex_topics is stored as json (not jsonb), so we cast to jsonb for operations
    op.execute("""
        UPDATE search_talent_document doc
        SET search_text = doc.search_text || ' ' || COALESCE(
            (SELECT string_agg(value::text, ' ')
             FROM jsonb_array_elements_text(t.openalex_topics::jsonb)),
            ''
        )
        FROM core_talent t
        WHERE doc.talent_id = t.talent_id
          AND t.openalex_topics IS NOT NULL
          AND jsonb_array_length(t.openalex_topics::jsonb) > 0
          AND doc.search_text NOT LIKE '%' || COALESCE(
              (SELECT string_agg(value::text, ' ')
               FROM jsonb_array_elements_text(t.openalex_topics::jsonb)),
              ''
          ) || '%'
    """)


def downgrade() -> None:
    # Downgrade is not precisely reversible without storing the original search_text
    # The search_text will simply contain extra keywords, which is harmless
    pass
