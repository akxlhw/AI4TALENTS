"""Convert os_repo_config.tech_element from single VARCHAR to JSON array

Migration path (safe 3-step):
1. Add tech_element_new JSON column
2. Convert data: 'ai' → '["ai"]' via json_build_array
3. Drop old column, rename new column

Revision ID: 061
Revises: 060
Create Date: 2026-08-14

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert tech_element VARCHAR → JSONB array."""
    # 1. Add new JSONB column
    op.execute("ALTER TABLE os_repo_config ADD COLUMN tech_element_new JSONB")

    # 2. Convert data: 'ai' → '["ai"]' (handles NULL gracefully)
    op.execute(
        "UPDATE os_repo_config "
        "SET tech_element_new = CASE "
        "  WHEN tech_element IS NULL OR tech_element = '' THEN '[]'::jsonb "
        "  ELSE jsonb_build_array(tech_element) "
        "END"
    )

    # 3. Drop old column, rename new
    op.execute("ALTER TABLE os_repo_config DROP COLUMN tech_element")
    op.execute("ALTER TABLE os_repo_config RENAME COLUMN tech_element_new TO tech_element")

    # Recreate index — GIN with jsonb_path_ops supports @> contains queries
    op.execute(
        "CREATE INDEX ix_os_repo_config_tech_element "
        "ON os_repo_config USING GIN (tech_element jsonb_path_ops)"
    )


def downgrade() -> None:
    """Revert JSON array → single VARCHAR (keeps first element only)."""
    op.execute("ALTER TABLE os_repo_config ADD COLUMN tech_element_old VARCHAR(50)")
    op.execute(
        "UPDATE os_repo_config "
        "SET tech_element_old = CASE "
        "  WHEN tech_element IS NULL OR json_array_length(tech_element) = 0 THEN NULL "
        "  ELSE tech_element->>0 "
        "END"
    )
    op.execute("ALTER TABLE os_repo_config DROP COLUMN tech_element")
    op.execute("ALTER TABLE os_repo_config RENAME COLUMN tech_element_old TO tech_element")
    op.execute("CREATE INDEX ix_os_repo_config_tech_element ON os_repo_config (tech_element)")
