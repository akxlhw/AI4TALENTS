"""Remove core_country table, add country columns to core_school

Revision ID: 022
Revises: 021
Create Date: 2026-04-02
Updated: 2026-04-03 - Fix SQLite foreign key constraint issue

This migration:
1. Adds country_code and country_name columns to core_school
2. Drops the country_id foreign key constraint
3. Drops the core_country table

Note: For SQLite, we must recreate the table to drop a column with FK constraint.
SQLite 3.35.0+ supports ALTER TABLE DROP COLUMN, but it fails when the column
has a foreign key reference. The workaround is to recreate the table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    """Check if the database is SQLite."""
    conn = op.get_bind()
    return conn.dialect.name == 'sqlite'


def upgrade() -> None:
    # Step 1: Add new country columns to core_school
    op.add_column(
        'core_school',
        sa.Column('country_code', sa.String(10), nullable=True, default='XX')
    )
    op.add_column(
        'core_school',
        sa.Column('country_name', sa.String(100), nullable=True)
    )

    # Step 2: Create index on country_code
    op.create_index('ix_core_school_country_code', 'core_school', ['country_code'])

    if _is_sqlite():
        # SQLite: Recreate table without country_id to avoid FK constraint issue
        conn = op.get_bind()

        # Create new table without country_id and without FK
        conn.execute(text('''
            CREATE TABLE core_school_new (
                school_id INTEGER PRIMARY KEY,
                school_name VARCHAR(255) NOT NULL,
                school_alias VARCHAR(255),
                school_intro TEXT,
                homepage_url VARCHAR(500),
                professor_count INTEGER DEFAULT 0,
                student_count INTEGER DEFAULT 0,
                is_visible BOOLEAN DEFAULT 1 NOT NULL,
                status VARCHAR(20) DEFAULT 'active' NOT NULL,
                source_type VARCHAR(50),
                source_record_id VARCHAR(100),
                last_sync_batch_id INTEGER,
                department_name VARCHAR(255),
                lab_name VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME,
                is_top_school BOOLEAN DEFAULT 0 NOT NULL,
                country_code VARCHAR(10) DEFAULT 'XX' NOT NULL,
                country_name VARCHAR(100)
            )
        '''))

        # Copy data (excluding country_id)
        conn.execute(text('''
            INSERT INTO core_school_new
            SELECT school_id, school_name, school_alias, school_intro, homepage_url,
                   professor_count, student_count, is_visible, status, source_type,
                   source_record_id, last_sync_batch_id, department_name, lab_name,
                   created_at, updated_at, is_top_school, country_code, country_name
            FROM core_school
        '''))

        # Drop old table and rename
        conn.execute(text('DROP TABLE core_school'))
        conn.execute(text('ALTER TABLE core_school_new RENAME TO core_school'))

        # Recreate indexes
        conn.execute(text('CREATE INDEX ix_core_school_school_id ON core_school (school_id)'))
        conn.execute(text('CREATE INDEX ix_core_school_school_name ON core_school (school_name)'))
        conn.execute(text('CREATE INDEX ix_core_school_source_record_id ON core_school (source_record_id)'))
        conn.execute(text('CREATE INDEX ix_core_school_country_code ON core_school (country_code)'))
        conn.execute(text('CREATE INDEX ix_core_school_is_top_school ON core_school (is_top_school)'))
    else:
        # PostgreSQL: Can use standard operations
        conn = op.get_bind()
        # Check if foreign key exists before dropping
        result = conn.execute(text("""
            SELECT conname FROM pg_catalog.pg_constraint
            WHERE conrelid = 'core_school'::regclass
            AND contype = 'f'
            AND conname = 'fk_core_school_country_id_core_country'
        """))
        if result.fetchone():
            op.drop_constraint('fk_core_school_country_id_core_country', 'core_school', type_='foreignkey')

        # Check if column exists before dropping
        result = conn.execute(text("""
            SELECT attname FROM pg_catalog.pg_attribute
            WHERE attrelid = 'core_school'::regclass AND attname = 'country_id'
            AND attnum > 0 AND NOT attisdropped
        """))
        if result.fetchone():
            op.drop_column('core_school', 'country_id')

    # Step 3: Drop core_country table (if exists)
    conn = op.get_bind()

    # First, drop any foreign keys referencing core_country
    result = conn.execute(text("""
        SELECT cl.relname AS table_name, con.conname AS constraint_name
        FROM pg_catalog.pg_constraint con
        JOIN pg_catalog.pg_class cl ON con.conrelid = cl.oid
        JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid
        WHERE con.contype = 'f'
        AND ns.nspname = 'public'
        AND cl.relname != 'core_school'
        AND EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = con.conrelid
            AND a.attnum = ANY(con.conkey)
            AND a.attname = 'country_id'
        )
    """))
    for row in result.fetchall():
        table_name, constraint_name = row
        op.drop_constraint(constraint_name, table_name, type_='foreignkey')

    # Also drop country_id columns from other tables
    result = conn.execute(text("""
        SELECT c.relname AS table_name
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE a.attname = 'country_id' AND c.relname NOT IN ('core_school', 'core_country')
        AND n.nspname = 'public' AND c.relkind = 'r'
        AND a.attnum > 0 AND NOT a.attisdropped
    """))
    for row in result.fetchall():
        table_name = row[0]
        op.drop_column(table_name, 'country_id')

    # Now check if core_country exists and drop it
    result = conn.execute(text("""
        SELECT c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'core_country'
    """))
    if result.fetchone():
        op.drop_table('core_country')


def downgrade() -> None:
    # Step 1: Recreate core_country table
    op.create_table(
        'core_country',
        sa.Column('country_id', sa.Integer(), primary_key=True),
        sa.Column('country_code', sa.String(10), unique=True, nullable=False),
        sa.Column('country_name_cn', sa.String(100), nullable=False),
        sa.Column('country_name_en', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_core_country_country_id', 'core_country', ['country_id'])
    op.create_index('ix_core_country_country_code', 'core_country', ['country_code'])

    if _is_sqlite():
        # SQLite: Recreate table with country_id column
        conn = op.get_bind()

        conn.execute(text('''
            CREATE TABLE core_school_new (
                school_id INTEGER PRIMARY KEY,
                school_name VARCHAR(255) NOT NULL,
                school_alias VARCHAR(255),
                country_id INTEGER REFERENCES core_country(country_id),
                school_intro TEXT,
                homepage_url VARCHAR(500),
                professor_count INTEGER DEFAULT 0,
                student_count INTEGER DEFAULT 0,
                is_visible BOOLEAN DEFAULT 1 NOT NULL,
                status VARCHAR(20) DEFAULT 'active' NOT NULL,
                source_type VARCHAR(50),
                source_record_id VARCHAR(100),
                last_sync_batch_id INTEGER,
                department_name VARCHAR(255),
                lab_name VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME,
                is_top_school BOOLEAN DEFAULT 0 NOT NULL
            )
        '''))

        conn.execute(text('''
            INSERT INTO core_school_new
            SELECT school_id, school_name, school_alias, NULL as country_id,
                   school_intro, homepage_url, professor_count, student_count,
                   is_visible, status, source_type, source_record_id, last_sync_batch_id,
                   department_name, lab_name, created_at, updated_at, is_top_school
            FROM core_school
        '''))

        conn.execute(text('DROP TABLE core_school'))
        conn.execute(text('ALTER TABLE core_school_new RENAME TO core_school'))

        # Recreate indexes
        conn.execute(text('CREATE INDEX ix_core_school_school_id ON core_school (school_id)'))
        conn.execute(text('CREATE INDEX ix_core_school_school_name ON core_school (school_name)'))
        conn.execute(text('CREATE INDEX ix_core_school_source_record_id ON core_school (source_record_id)'))
        conn.execute(text('CREATE INDEX ix_core_school_country_id ON core_school (country_id)'))
        conn.execute(text('CREATE INDEX ix_core_school_is_top_school ON core_school (is_top_school)'))
    else:
        # PostgreSQL: Standard operations
        op.add_column(
            'core_school',
            sa.Column('country_id', sa.Integer(), sa.ForeignKey('core_country.country_id'), nullable=True)
        )
        op.create_index('ix_core_school_country_id', 'core_school', ['country_id'])
        op.drop_index('ix_core_school_country_code', 'core_school')
        op.drop_column('core_school', 'country_code')
        op.drop_column('core_school', 'country_name')
