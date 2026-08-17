"""add social_links to os_developer

Revision ID: 064
Revises: 063
Create Date: 2026-08-16

The collector parsed twitter_username from GitHub profiles but the model and
sync allowlist never persisted it, and profiles carry more than Twitter
(LinkedIn / personal sites via the blog field). Store a normalized
platform → URL map (JSONB), e.g. {"twitter": "https://x.com/…",
"linkedin": "https://www.linkedin.com/in/…", "website": "https://…"}.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "064"
down_revision: Union[str, None] = "063"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "os_developer",
        sa.Column("social_links", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("os_developer", "social_links")
