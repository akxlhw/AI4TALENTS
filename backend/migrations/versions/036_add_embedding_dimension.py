"""Add embedding dimension configuration

Revision ID: 036
Revises: 035
Create Date: 2026-04-21

This migration adds:
- LLM_EMBEDDING_DIMENSION: Configurable embedding vector dimension
- Modifies vector column from vector(1536) to vector(1024) for Qwen embedding

Note: Changing vector dimension will clear existing embeddings.
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add embedding dimension configuration and modify vector column."""
    conn: Connection = op.get_bind()

    # Check if PostgreSQL
    is_postgres = conn.dialect.name == 'postgresql'

    # 1. Add configuration key
    conn.execute(text("""
        INSERT INTO sys_config (config_key, config_value, config_type, is_sensitive, description, created_at, updated_at)
        VALUES ('LLM_EMBEDDING_DIMENSION', '1024', 'int', false, '嵌入向量维度 (128-4096)', NOW(), NOW())
        ON CONFLICT (config_key) DO NOTHING
    """))

    if is_postgres:
        # 2. Drop vector index
        conn.execute(text("DROP INDEX IF EXISTS ix_talent_embedding_vector"))

        # 3. Clear existing embeddings (required before changing dimension)
        conn.execute(text("DELETE FROM core_talent_embedding"))

        # 4. Modify vector column dimension
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            ALTER COLUMN embedding TYPE vector(1024)
        """))

        # 5. Recreate vector index
        conn.execute(text("""
            CREATE INDEX ix_talent_embedding_vector
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))


def downgrade() -> None:
    """Remove embedding dimension configuration and restore vector column."""
    conn: Connection = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'

    # Remove configuration
    conn.execute(text("DELETE FROM sys_config WHERE config_key = 'LLM_EMBEDDING_DIMENSION'"))

    if is_postgres:
        # Drop index
        conn.execute(text("DROP INDEX IF EXISTS ix_talent_embedding_vector"))

        # Clear data
        conn.execute(text("DELETE FROM core_talent_embedding"))

        # Restore to 1536
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            ALTER COLUMN embedding TYPE vector(1536)
        """))

        # Recreate index
        conn.execute(text("""
            CREATE INDEX ix_talent_embedding_vector
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
