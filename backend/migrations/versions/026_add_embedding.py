"""Add vector embedding support for v1.4

Revision ID: 026
Revises: 025
Create Date: 2026-04-11

This migration adds vector embedding capabilities:
1. pgvector extension for vector similarity search
2. core_talent_embedding table for storing embeddings
"""
from alembic import op
from sqlalchemy import text, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the database is PostgreSQL."""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Add vector embedding support."""
    is_pg = _is_postgres()

    if is_pg:
        # Enable pgvector extension
        op.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

        # Create embedding table
        op.execute(text('''
            CREATE TABLE IF NOT EXISTS core_talent_embedding (
                embedding_id SERIAL PRIMARY KEY,
                talent_id INTEGER NOT NULL REFERENCES core_talent(talent_id) ON DELETE CASCADE,
                embedding vector(1536) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                source_text_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_talent_embedding_talent_id UNIQUE (talent_id)
            )
        '''))

        # Create index on model_name for filtering
        op.create_index(
            'ix_talent_embedding_model',
            'core_talent_embedding',
            ['model_name'],
        )

        # Create vector index for similarity search (IVFFlat for larger datasets)
        # Note: Requires sufficient data for optimal performance
        op.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_talent_embedding_vector
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        '''))

    else:
        # SQLite: Store embeddings as JSON (limited functionality)
        op.create_table(
            'core_talent_embedding',
            Column('embedding_id', Integer, primary_key=True, autoincrement=True),
            Column('talent_id', Integer, nullable=False, unique=True),
            Column('embedding', JSON, nullable=False),
            Column('model_name', String(100), nullable=False),
            Column('source_text_hash', String(64), nullable=False),
            Column('created_at', DateTime, nullable=False),
            Column('updated_at', DateTime, nullable=False),
        )

        op.create_index(
            'ix_talent_embedding_model',
            'core_talent_embedding',
            ['model_name'],
        )


def downgrade() -> None:
    """Remove vector embedding support."""
    is_pg = _is_postgres()

    # Drop table
    op.drop_table('core_talent_embedding')

    if is_pg:
        # Drop extension (cascade will drop dependent objects)
        op.execute(text('DROP EXTENSION IF EXISTS vector CASCADE'))
