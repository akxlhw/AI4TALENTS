"""add resume_at to os_collect_task (rate-limit auto-resume)

Revision ID: 063
Revises: 062
Create Date: 2026-08-16

rate_limited tasks carry resume_at = limited_at + retry_after; a background
loop restarts them once the GitHub reset window passes.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "063"
down_revision: Union[str, None] = "062"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "os_collect_task",
        sa.Column("resume_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("os_collect_task", "resume_at")
