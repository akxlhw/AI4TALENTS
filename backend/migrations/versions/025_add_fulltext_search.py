"""Add full-text search support for v1.4

Revision ID: 025
Revises: 024
Create Date: 2026-04-11

This migration adds full-text search capabilities:
1. pg_trgm extension for trigram similarity
2. tsvector column for search documents
3. GIN indexes for fast full-text search
"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the database is PostgreSQL."""
    conn = op.get_bind()
    return conn.dialect.name == 'postgresql'


def upgrade() -> None:
    """Add full-text search support."""
    is_pg = _is_postgres()

    if is_pg:
        # Enable pg_trgm extension for trigram similarity
        op.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))

        # Add search_vector column to search_talent_document if not exists
        op.execute(text('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'search_talent_document'
                    AND column_name = 'search_vector'
                ) THEN
                    ALTER TABLE search_talent_document
                    ADD COLUMN search_vector tsvector;
                END IF;
            END $$;
        '''))

        # Create GIN index for full-text search
        op.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_search_talent_document_vector
            ON search_talent_document USING GIN(search_vector)
        '''))

        # Create trigram index for fuzzy search on name
        op.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_search_talent_document_name_trgm
            ON search_talent_document USING GIN(name gin_trgm_ops)
        '''))

        # Create function to update search_vector
        op.execute(text('''
            CREATE OR REPLACE FUNCTION update_search_talent_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.school_name, '')), 'B') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.search_text, '')), 'C');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        '''))

        # Create trigger to auto-update search_vector
        op.execute(text('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_update_search_vector'
                ) THEN
                    CREATE TRIGGER trigger_update_search_vector
                    BEFORE INSERT OR UPDATE ON search_talent_document
                    FOR EACH ROW EXECUTE FUNCTION update_search_talent_vector();
                END IF;
            END $$;
        '''))

        # Update existing records
        op.execute(text('''
            UPDATE search_talent_document
            SET search_vector =
                setweight(to_tsvector('simple', COALESCE(name, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(school_name, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(search_text, '')), 'C')
            WHERE search_vector IS NULL
        '''))

    else:
        # SQLite: Create simple FTS5 virtual table if possible
        # Note: FTS5 may not be available in all SQLite builds
        op.execute(text('''
            CREATE TABLE IF NOT EXISTS search_talent_fts (
                rowid INTEGER PRIMARY KEY,
                talent_id INTEGER,
                name TEXT,
                school_name TEXT,
                search_text TEXT
            )
        '''))

        # Create index on talent_id for lookups
        op.create_index(
            'ix_search_talent_fts_talent_id',
            'search_talent_fts',
            ['talent_id'],
            unique=True,
        )


def downgrade() -> None:
    """Remove full-text search support."""
    is_pg = _is_postgres()

    if is_pg:
        # Drop trigger
        op.execute(text('''
            DROP TRIGGER IF EXISTS trigger_update_search_vector ON search_talent_document
        '''))

        # Drop function
        op.execute(text('DROP FUNCTION IF EXISTS update_search_talent_vector()'))

        # Drop indexes
        op.execute(text('DROP INDEX IF EXISTS ix_search_talent_document_name_trgm'))
        op.execute(text('DROP INDEX IF EXISTS ix_search_talent_document_vector'))

        # Drop column
        op.execute(text('''
            ALTER TABLE search_talent_document DROP COLUMN IF EXISTS search_vector
        '''))

    else:
        # SQLite: Drop FTS table
        op.execute(text('DROP TABLE IF EXISTS search_talent_fts'))
