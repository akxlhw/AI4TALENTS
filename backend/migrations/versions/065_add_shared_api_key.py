"""Add shared_api_key table for the open API.

Revision ID: 065
Revises: 064
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "065"
down_revision: Union[str, None] = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_api_key",
        sa.Column("api_key_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key_name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=8), nullable=False),
        sa.Column("scopes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("api_key_id"),
    )
    op.create_index("ix_shared_api_key_api_key_id", "shared_api_key", ["api_key_id"])
    op.create_index(
        "ix_shared_api_key_key_hash", "shared_api_key", ["key_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_shared_api_key_key_hash", table_name="shared_api_key")
    op.drop_index("ix_shared_api_key_api_key_id", table_name="shared_api_key")
    op.drop_table("shared_api_key")
