"""Upgrade os_embedding to pgvector

Revision ID: 047
Revises: 046
Create Date: 2026-05-05

This migration upgrades the open-source embedding table to use pgvector,
aligning it with the academic talent embedding table for unified dimension
management.
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision: str = '047'
down_revision: str | None = '046'
branch_labels = None
depends_on = None


def _get_embedding_dimension(conn: Connection) -> int:
    """Read current embedding dimension from sys_config, default to 1024."""
    result = conn.execute(
        text("SELECT config_value FROM sys_config WHERE config_key = 'LLM_EMBEDDING_DIMENSION'")
    )
    row = result.fetchone()
    if row and row[0]:
        try:
            return int(row[0])
        except ValueError:
            pass
    return 1024


def upgrade() -> None:
    """Upgrade os_embedding to pgvector."""
    conn: Connection = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'

    if not is_postgres:
        # Non-PostgreSQL: keep TEXT/JSON storage, nothing to do
        return

    # Ensure pgvector extension is available
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Read current dimension from config
    dimension = _get_embedding_dimension(conn)

    # Drop existing hash index (will be recreated after column type change)
    conn.execute(text("DROP INDEX IF EXISTS ix_os_embedding_hash"))

    # Clear existing embeddings (required before changing column type)
    conn.execute(text("DELETE FROM os_embedding"))

    # Alter column type from TEXT to vector(N)
    # USING required: PostgreSQL has no implicit cast from TEXT to vector
    conn.execute(
        text(f"""
            ALTER TABLE os_embedding
            ALTER COLUMN embedding TYPE vector({dimension})
            USING embedding::vector({dimension})
        """)
    )

    # Recreate hash index
    conn.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_os_embedding_hash
            ON os_embedding (source_text_hash)
        """)
    )

    # Create vector similarity index (IVFFlat for larger datasets)
    conn.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_os_embedding_vector
            ON os_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
    )


def downgrade() -> None:
    """Downgrade os_embedding back to TEXT."""
    conn: Connection = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'

    if not is_postgres:
        return

    # Drop vector index
    conn.execute(text("DROP INDEX IF EXISTS ix_os_embedding_vector"))

    # Clear data before type change
    conn.execute(text("DELETE FROM os_embedding"))

    # Revert column type to TEXT
    conn.execute(
        text("""
            ALTER TABLE os_embedding
            ALTER COLUMN embedding TYPE TEXT
            USING embedding::TEXT
        """)
    )

    # Recreate hash index
    conn.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_os_embedding_hash
            ON os_embedding (source_text_hash)
        """)
    )
