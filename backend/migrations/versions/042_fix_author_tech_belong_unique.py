"""Fix AuthorTechBelong unique constraint to include venue

Revision ID: 042
Revises: 041_add_missing_indexes
Create Date: 2026-04-28

The original unique constraint (openalex_author_id, tech_domain_id) assumed
an author belongs to at most one venue per tech domain. In practice, authors
publish in multiple venues within the same domain (e.g., NeurIPS and ICML
both map to AI). This caused integrity errors during bulk collection.

This migration:
1. Drops the old unique index on (author_id, tech_domain_id)
2. Creates a new unique index on (author_id, tech_domain_id, source_venue_id)

Downstream sync (tech_tag_sync) now aggregates work_count across venues
before creating TalentTechTag records.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '042'
down_revision = '041'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old unique index (actual name in DB is ix_author_tech_belong)
    op.drop_index('ix_author_tech_belong', table_name='rel_author_tech_belong')

    # Create the new unique index including source_venue_id
    op.create_index(
        'ix_author_tech_author_domain_venue',
        'rel_author_tech_belong',
        ['openalex_author_id', 'tech_domain_id', 'source_venue_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_author_tech_author_domain_venue', table_name='rel_author_tech_belong')
    op.create_index(
        'ix_author_tech_belong',
        'rel_author_tech_belong',
        ['openalex_author_id', 'tech_domain_id'],
        unique=True,
    )
