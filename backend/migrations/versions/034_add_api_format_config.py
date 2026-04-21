"""Add API format configuration for LLM services

Revision ID: 034
Revises: 033
Create Date: 2026-04-21

This migration adds:
1. LLM_API_FORMAT - API format for chat model (openai/minimax)
2. LLM_EMBEDDING_API_FORMAT - API format for embedding model (defaults to LLM_API_FORMAT)

This replaces the implicit provider detection with explicit API format selection.
"""
from datetime import datetime

from alembic import op
from sqlalchemy import column, table
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add LLM_API_FORMAT and LLM_EMBEDDING_API_FORMAT configuration keys."""
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

    # Insert API format configuration for chat model
    conn.execute(
        system_config.insert().values(
            config_key='LLM_API_FORMAT',
            config_value='openai',
            config_type='string',
            is_sensitive=False,
            description='对话模型 API 格式 (openai: OpenAI兼容格式, minimax: MiniMax专用格式)',
            created_at=now,
            updated_at=now,
        )
    )

    # Insert API format configuration for embedding model
    conn.execute(
        system_config.insert().values(
            config_key='LLM_EMBEDDING_API_FORMAT',
            config_value='',
            config_type='string',
            is_sensitive=False,
            description='嵌入模型 API 格式 (留空则使用对话模型 API 格式)',
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    """Remove LLM_API_FORMAT and LLM_EMBEDDING_API_FORMAT configuration keys."""
    conn: Connection = op.get_bind()
    conn.execute(
        "DELETE FROM sys_config WHERE config_key IN ('LLM_API_FORMAT', 'LLM_EMBEDDING_API_FORMAT')"
    )
