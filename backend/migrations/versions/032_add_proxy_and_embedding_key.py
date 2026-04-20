"""Add proxy and embedding API key configuration

Revision ID: 032
Revises: 031
Create Date: 2026-04-19

This migration adds configuration keys for:
1. HTTP proxy settings (for enterprise intranet access)
2. Independent embedding API key (for separate LLM/embedding services)
"""
from datetime import datetime

from alembic import op
from sqlalchemy import column, table
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add proxy and embedding API key configuration keys."""
    # Get database connection
    conn: Connection = op.get_bind()

    # Define the system_config table for insert
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

    # Insert proxy configuration keys
    proxy_configs = [
        {
            'config_key': 'PROXY_ENABLED',
            'config_value': 'false',
            'config_type': 'bool',
            'is_sensitive': False,
            'description': '启用 HTTP 代理访问外网',
            'created_at': now,
            'updated_at': now,
        },
        {
            'config_key': 'PROXY_URL',
            'config_value': '',
            'config_type': 'string',
            'is_sensitive': False,
            'description': '代理服务器地址 (如 http://proxy.company.com:8080)',
            'created_at': now,
            'updated_at': now,
        },
        {
            'config_key': 'PROXY_USERNAME',
            'config_value': '',
            'config_type': 'string',
            'is_sensitive': False,
            'description': '代理服务器用户名 (可选)',
            'created_at': now,
            'updated_at': now,
        },
        {
            'config_key': 'PROXY_PASSWORD',
            'config_value': '',
            'config_type': 'string',
            'is_sensitive': True,
            'description': '代理服务器密码 (可选)',
            'created_at': now,
            'updated_at': now,
        },
        {
            'config_key': 'LLM_EMBEDDING_API_KEY',
            'config_value': '',
            'config_type': 'string',
            'is_sensitive': True,
            'description': '嵌入服务独立 API Key (留空则使用对话 API Key)',
            'created_at': now,
            'updated_at': now,
        },
    ]

    for config in proxy_configs:
        conn.execute(
            system_config.insert().values(**config)
        )


def downgrade() -> None:
    """Remove proxy configuration keys."""
    conn: Connection = op.get_bind()

    keys_to_remove = [
        'PROXY_ENABLED',
        'PROXY_URL',
        'PROXY_USERNAME',
        'PROXY_PASSWORD',
        'LLM_EMBEDDING_API_KEY',
    ]

    for key in keys_to_remove:
        conn.execute(
            f"DELETE FROM sys_config WHERE config_key = '{key}'"
        )
