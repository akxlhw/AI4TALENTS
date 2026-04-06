"""Add performance indexes for v1.3

Revision ID: 023
Revises: 022
Create Date: 2026-04-06

This migration creates performance-optimized indexes for:
1. User-visible pages (P0): talent list, tech element pages, favorites
2. Collection tasks (P1): raw data processing queries

For PostgreSQL:
- Creates descending indexes for sorted queries
- Creates partial indexes for filtered queries

For SQLite:
- Creates standard indexes (no DESC or partial index support)
"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the database is PostgreSQL."""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Create performance indexes."""
    is_pg = _is_postgres()

    # ========================================
    # P0: User-visible page indexes
    # ========================================

    # Talent list page: filter by school + role, sorted by citations
    # Query pattern: WHERE is_visible = true AND school_id = ? AND role_type = ?
    op.create_index(
        'ix_core_talent_visible_school_role',
        'core_talent',
        ['is_visible', 'school_id', 'role_type'],
        unique=False,
    )

    # Talent list page: visible talents sorted by citations
    # Query pattern: WHERE is_visible = true ORDER BY cited_by_count DESC
    if is_pg:
        # PostgreSQL supports DESC index
        op.execute(text(
            "CREATE INDEX ix_core_talent_visible_cited_desc "
            "ON core_talent (is_visible, cited_by_count DESC)"
        ))
    else:
        # SQLite: standard index
        op.create_index(
            'ix_core_talent_visible_cited_desc',
            'core_talent',
            ['is_visible', 'cited_by_count'],
            unique=False,
        )

    # Tech element page: get talents by tech element
    # Query pattern: WHERE is_enabled = true AND tech_element_id = ?
    if is_pg:
        # PostgreSQL partial index for enabled tags only
        op.execute(text(
            "CREATE INDEX ix_talent_tech_enabled_element "
            "ON core_talent_tech_tag (is_enabled, tech_element_id, talent_id) "
            "WHERE is_enabled = true"
        ))
    else:
        op.create_index(
            'ix_talent_tech_enabled_element',
            'core_talent_tech_tag',
            ['is_enabled', 'tech_element_id', 'talent_id'],
            unique=False,
        )

    # Tech element page: get talents by tech direction
    # Query pattern: WHERE is_enabled = true AND tech_direction_id = ?
    if is_pg:
        op.execute(text(
            "CREATE INDEX ix_talent_tech_enabled_direction "
            "ON core_talent_tech_tag (is_enabled, tech_direction_id, talent_id) "
            "WHERE is_enabled = true"
        ))
    else:
        op.create_index(
            'ix_talent_tech_enabled_direction',
            'core_talent_tech_tag',
            ['is_enabled', 'tech_direction_id', 'talent_id'],
            unique=False,
        )

    # Favorites page: user's favorites sorted by creation time
    # Query pattern: WHERE user_id = ? AND is_active = true ORDER BY created_at DESC
    if is_pg:
        op.execute(text(
            "CREATE INDEX ix_favorite_user_active_created "
            "ON iam_favorite_talent (user_id, is_active, created_at DESC) "
            "WHERE is_active = true"
        ))
    else:
        op.create_index(
            'ix_favorite_user_active_created',
            'iam_favorite_talent',
            ['user_id', 'is_active', 'created_at'],
            unique=False,
        )

    # ========================================
    # P1: Collection task indexes
    # ========================================

    # Collection: get works by source and year range
    # Query pattern: WHERE source_id = ? AND publication_year >= ? AND publication_year <= ?
    op.create_index(
        'ix_raw_work_source_year',
        'raw_work',
        ['source_id', 'publication_year'],
        unique=False,
    )

    # Normalization: get pending authors by task
    # Query pattern: WHERE processed_status = 'pending' AND fetch_task_id = ?
    op.create_index(
        'ix_raw_author_status_task',
        'raw_author',
        ['processed_status', 'fetch_task_id'],
        unique=False,
    )

    # Normalization: get pending institutions by task
    # Query pattern: WHERE processed_status = 'pending' AND fetch_task_id = ?
    op.create_index(
        'ix_raw_inst_status_task',
        'raw_institution',
        ['processed_status', 'fetch_task_id'],
        unique=False,
    )


def downgrade() -> None:
    """Remove performance indexes."""
    # P0 indexes
    op.drop_index('ix_favorite_user_active_created', 'iam_favorite_talent')
    op.drop_index('ix_talent_tech_enabled_direction', 'core_talent_tech_tag')
    op.drop_index('ix_talent_tech_enabled_element', 'core_talent_tech_tag')
    op.drop_index('ix_core_talent_visible_cited_desc', 'core_talent')
    op.drop_index('ix_core_talent_visible_school_role', 'core_talent')

    # P1 indexes
    op.drop_index('ix_raw_inst_status_task', 'raw_institution')
    op.drop_index('ix_raw_author_status_task', 'raw_author')
    op.drop_index('ix_raw_work_source_year', 'raw_work')
