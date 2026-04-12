"""Add system config table for v1.4

Revision ID: 028
Revises: 027
Create Date: 2026-04-12

This migration adds system configuration table:
1. sys_config: Key-value store for system configuration including LLM settings
"""
from alembic import op
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime


# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add system config table."""
    # Create sys_config table
    op.create_table(
        'sys_config',
        Column('config_id', Integer, primary_key=True, autoincrement=True),
        Column('config_key', String(100), unique=True, nullable=False),
        Column('config_value', Text, nullable=True),
        Column('config_type', String(20), nullable=False, server_default='string'),
        Column('is_sensitive', Boolean, nullable=False, server_default='false'),
        Column('description', String(500), nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
    )

    # Create indexes
    op.create_index(
        'ix_sys_config_key',
        'sys_config',
        ['config_key'],
    )

    # Insert default LLM configuration values
    op.execute("""
        INSERT INTO sys_config (config_key, config_value, config_type, is_sensitive, description, created_at, updated_at)
        VALUES
            ('LLM_ENABLED', 'false', 'bool', false, '启用 LLM 功能', NOW(), NOW()),
            ('LLM_PROVIDER', 'deepseek', 'string', false, 'LLM 服务商 (deepseek/openai/zhipu/qwen/custom)', NOW(), NOW()),
            ('LLM_API_KEY', '', 'string', true, 'API 密钥', NOW(), NOW()),
            ('LLM_API_BASE', '', 'string', false, 'API 基础地址', NOW(), NOW()),
            ('LLM_MODEL', 'deepseek-chat', 'string', false, '对话模型名称', NOW(), NOW()),
            ('LLM_EMBEDDING_MODEL', '', 'string', false, '嵌入模型名称', NOW(), NOW()),
            ('LLM_TIMEOUT', '60', 'int', false, 'API 请求超时时间（秒）', NOW(), NOW())
    """)


def downgrade() -> None:
    """Remove system config table."""
    op.drop_table('sys_config')
