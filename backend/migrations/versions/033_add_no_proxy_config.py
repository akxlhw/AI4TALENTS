"""Add no_proxy configuration for enterprise intranet deployment

Revision ID: 033
Revises: 032
Create Date: 2026-04-19

This migration adds the PROXY_NO_PROXY configuration key for specifying
addresses that should bypass the proxy (e.g., internal LLM services).

Typical values:
- localhost,127.0.0.1,*.internal.com,10.*,192.168.*
"""
from datetime import datetime

from alembic import op
from sqlalchemy import column, table
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add PROXY_NO_PROXY configuration key."""
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

    # Insert no_proxy configuration
    conn.execute(
        system_config.insert().values(
            config_key='PROXY_NO_PROXY',
            config_value='',
            config_type='string',
            is_sensitive=False,
            description='不走代理的地址列表 (逗号分隔，如 localhost,127.0.0.1,*.internal.com,10.*,192.168.*)',
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    """Remove PROXY_NO_PROXY configuration key."""
    conn: Connection = op.get_bind()
    conn.execute(
        "DELETE FROM sys_config WHERE config_key = 'PROXY_NO_PROXY'"
    )
