"""Add last_completed_phase to sync_collect_task.

Revision ID: 048
Revises: 047
Create Date: 2026-05-06 21:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "048"
down_revision: Union[str, None] = "047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sync_collect_task",
        sa.Column("last_completed_phase", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sync_collect_task", "last_completed_phase")
