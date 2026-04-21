"""Add LLM_EMBEDDING_ENABLED configuration

Revision ID: 035
Revises: 034
Create Date: 2026-04-21

This migration adds:
- LLM_EMBEDDING_ENABLED: Independent enable switch for embedding model

This allows users to enable chat model and embedding model independently.
"""
from datetime import datetime

from alembic import op
from sqlalchemy import column, table
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add LLM_EMBEDDING_ENABLED configuration key."""
    conn: Connection = op.get_bind()

    system_config = table(
        'sys_config',
        column('config_key'),
        column('config_value'),
        column('config_type'),
        column('is_sensitive'),
        column('description'),
        column('created_at'),
        column('updated_at'),
    )

    now = datetime.utcnow()

    # Insert embedding enabled configuration
    conn.execute(
        system_config.insert().values(
            config_key='LLM_EMBEDDING_ENABLED',
            config_value='false',
            config_type='bool',
            is_sensitive=False,
            description='启用嵌入模型功能（语义搜索、相似人才推荐）',
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    """Remove LLM_EMBEDDING_ENABLED configuration key."""
    conn: Connection = op.get_bind()
    conn.execute(
        "DELETE FROM sys_config WHERE config_key = 'LLM_EMBEDDING_ENABLED'"
    )
