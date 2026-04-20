"""Add no_proxy and SSL verify configuration for enterprise intranet deployment

Revision ID: 033
Revises: 032
Create Date: 2026-04-19

This migration adds:
1. PROXY_NO_PROXY - addresses that should bypass the proxy
2. PROXY_SSL_VERIFY - whether to verify SSL certificates (for self-signed certs)
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
    """Add PROXY_NO_PROXY and PROXY_SSL_VERIFY configuration keys."""
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

    # Insert SSL verify configuration
    conn.execute(
        system_config.insert().values(
            config_key='PROXY_SSL_VERIFY',
            config_value='true',
            config_type='bool',
            is_sensitive=False,
            description='是否验证代理 SSL 证书 (企业自签名证书需设为 false)',
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    """Remove PROXY_NO_PROXY and PROXY_SSL_VERIFY configuration keys."""
    conn: Connection = op.get_bind()
    conn.execute(
        "DELETE FROM sys_config WHERE config_key IN ('PROXY_NO_PROXY', 'PROXY_SSL_VERIFY')"
    )
