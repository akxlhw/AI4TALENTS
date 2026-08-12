"""Drop orphan legacy tables (openalex_*, lw_*)

These tables were created by early migrations but their ORM models were
later removed from model_registry. They have no code references and are
pure database orphans. This migration drops them to bring alembic check
into alignment with the current model layer.

Revision ID: 059
Revises: 058
Create Date: 2026-08-12

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None

# Tables that exist in the database (via old migrations) but have no
# corresponding ORM model in model_registry.py. Verified: zero code
# references in app/ (the 'openalex_author' hits are column names like
# 'openalex_author_id', not table references).
_ORPHAN_TABLES = [
    "openalex_work_concept",
    "openalex_work_author",
    "openalex_source",
    "openalex_publisher",
    "openalex_funder",
    "openalex_institution",
    "openalex_concept",
    "openalex_work",
    "openalex_author",
    "lw_raw_person",
    "lw_collect_task",
    "lw_lab_registry",
]


def upgrade() -> None:
    """Drop orphan legacy tables that have no ORM model."""
    for table_name in _ORPHAN_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')


def downgrade() -> None:
    """Downgrade is not supported — recreating these legacy tables would
    require the original column definitions which are no longer maintained.
    If a rollback is truly needed, restore from a database backup."""
    pass
