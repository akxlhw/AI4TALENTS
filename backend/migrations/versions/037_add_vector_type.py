"""Add multi-vector type support

Revision ID: 037
Revises: 036
Create Date: 2026-04-21

This migration adds multi-vector support for semantic search:
1. Adds vector_type column to distinguish research vs papers embeddings
2. Changes unique constraint from (talent_id) to (talent_id, vector_type)
3. Creates partial indexes for each vector type

This enables:
- research: Vector generated from openalex_topics (research direction)
- papers: Vector generated from paper titles (research content)
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add multi-vector type support."""
    conn: Connection = op.get_bind()

    # Check if PostgreSQL
    is_postgres = conn.dialect.name == 'postgresql'

    if is_postgres:
        # 1. Drop existing unique constraint on talent_id
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            DROP CONSTRAINT IF EXISTS uq_talent_embedding_talent_id
        """))

        # 2. Drop existing vector index (will recreate as partial indexes)
        conn.execute(text("DROP INDEX IF EXISTS ix_talent_embedding_vector"))

        # 3. Add vector_type column with default 'research'
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            ADD COLUMN IF NOT EXISTS vector_type VARCHAR(20) NOT NULL DEFAULT 'research'
        """))

        # 4. Create unique constraint on (talent_id, vector_type)
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            ADD CONSTRAINT uq_talent_vector_type UNIQUE (talent_id, vector_type)
        """))

        # 5. Create index on vector_type for filtering
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_embedding_vector_type
            ON core_talent_embedding(vector_type)
        """))

        # 6. Create partial vector indexes for each type
        # Research vector index
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_embedding_research
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            WHERE vector_type = 'research'
        """))

        # Papers vector index
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_embedding_papers
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            WHERE vector_type = 'papers'
        """))

    else:
        # SQLite: Add vector_type column
        try:
            conn.execute(text("""
                ALTER TABLE core_talent_embedding
                ADD COLUMN vector_type VARCHAR(20) NOT NULL DEFAULT 'research'
            """))
        except Exception:
            # Column might already exist
            pass


def downgrade() -> None:
    """Remove multi-vector type support."""
    conn: Connection = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'

    if is_postgres:
        # 1. Drop partial indexes
        conn.execute(text("DROP INDEX IF EXISTS ix_embedding_papers"))
        conn.execute(text("DROP INDEX IF EXISTS ix_embedding_research"))
        conn.execute(text("DROP INDEX IF EXISTS ix_embedding_vector_type"))

        # 2. Drop unique constraint
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            DROP CONSTRAINT IF EXISTS uq_talent_vector_type
        """))

        # 3. Drop vector_type column
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            DROP COLUMN IF EXISTS vector_type
        """))

        # 4. Restore unique constraint on talent_id
        conn.execute(text("""
            ALTER TABLE core_talent_embedding
            ADD CONSTRAINT uq_talent_embedding_talent_id UNIQUE (talent_id)
        """))

        # 5. Recreate general vector index
        conn.execute(text("""
            CREATE INDEX ix_talent_embedding_vector
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))

    else:
        # SQLite: Drop vector_type column (requires table recreation)
        # For simplicity, we'll just note that downgrade is limited
        pass
