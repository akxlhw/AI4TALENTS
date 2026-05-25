"""add_school_talent_count_materialized_view

Revision ID: 99aed1b1b7e7
Revises: 7e6491a58f0e
Create Date: 2026-05-22 14:26:56.864601

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '99aed1b1b7e7'
down_revision: Union[str, None] = '7e6491a58f0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create materialized view for school talent count (affiliation口径).

    Counts talents associated with a school via ANY of the three fields:
    school_id, education_school_id, company_school_id.
    This aligns with the list/search query logic (OR condition).
    """
    op.execute("""
        CREATE MATERIALIZED VIEW mv_school_talent_count AS
        SELECT
            school_id,
            COUNT(*) AS talent_count,
            COUNT(*) FILTER (WHERE role_type = 'professor') AS professor_count,
            COUNT(*) FILTER (WHERE role_type IN ('student', 'graduate')) AS student_count
        FROM (
            SELECT talent_id, role_type, school_id
            FROM core_talent
            WHERE school_id IS NOT NULL AND is_visible = true
            UNION
            SELECT talent_id, role_type, education_school_id AS school_id
            FROM core_talent
            WHERE education_school_id IS NOT NULL AND is_visible = true
            UNION
            SELECT talent_id, role_type, company_school_id AS school_id
            FROM core_talent
            WHERE company_school_id IS NOT NULL AND is_visible = true
        ) t
        WHERE school_id IS NOT NULL
        GROUP BY school_id;
    """)

    # Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX idx_mv_school_talent_count_school_id
        ON mv_school_talent_count(school_id);
    """)

    # Index for fast ORDER BY talent_count DESC
    op.execute("""
        CREATE INDEX idx_mv_school_talent_count_count
        ON mv_school_talent_count(talent_count DESC);
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_school_talent_count CASCADE;")
