"""Simplify candidate statuses to 3: new, connected, terminated

Migrates existing industry_position_talent.status values:
  contacted, interviewed → connected
  rejected, hired        → terminated

Revision ID: 060
Revises: 059
Create Date: 2026-08-14

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert old 5-status values to new 3-status values."""
    op.execute(
        "UPDATE industry_position_talent SET status = 'connected' "
        "WHERE status IN ('contacted', 'interviewed')"
    )
    op.execute(
        "UPDATE industry_position_talent SET status = 'terminated' "
        "WHERE status IN ('rejected', 'hired')"
    )


def downgrade() -> None:
    """Cannot reverse — the old sub-statuses (contacted vs interviewed,
    rejected vs hired) are indistinguishable after migration."""
    pass
