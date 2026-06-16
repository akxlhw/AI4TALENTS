"""Add Venue configuration layer

Revision ID: 012
Revises: 011
Create Date: 2026-03-26

Changes:
1. Add config_venue table for independent venue management
2. Add config_venue_tech_binding table for venue-tech_element relationships
3. Add sync_venue_sub_task table for fine-grained collection tracking
4. Add is_top_school to core_school for Top院校 feature
5. Add time_window fields to sync_collect_task
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table (PostgreSQL compatible)."""
    result = conn.execute(sa.text(
        f"SELECT attname FROM pg_catalog.pg_attribute "
        f"WHERE attrelid = '{table_name}'::regclass AND attname = :column "
        f"AND attnum > 0 AND NOT attisdropped"
    ), {"column": column_name})
    return result.fetchone() is not None


def index_exists(conn, index_name):
    """Check if an index exists (PostgreSQL compatible)."""
    result = conn.execute(sa.text("""
        SELECT indexname FROM pg_indexes WHERE indexname = :index
    """), {"index": index_name})
    return result.fetchone() is not None


def upgrade():
    # Get connection
    conn = op.get_bind()

    # ============================================
    # Step 1: Add is_top_school to core_school (if not exists)
    # ============================================
    if not column_exists(conn, 'core_school', 'is_top_school'):
        with op.batch_alter_table('core_school', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_top_school', sa.Boolean, nullable=False, server_default='0'))

    # Create index if not exists
    if not index_exists(conn, 'ix_core_school_is_top'):
        op.create_index('ix_core_school_is_top', 'core_school', ['is_top_school'])

    # ============================================
    # Step 2: Add time_window to sync_collect_task (if not exists)
    # ============================================
    with op.batch_alter_table('sync_collect_task', schema=None) as batch_op:
        if not column_exists(conn, 'sync_collect_task', 'time_window_start'):
            batch_op.add_column(sa.Column('time_window_start', sa.DateTime, nullable=True))
        if not column_exists(conn, 'sync_collect_task', 'time_window_end'):
            batch_op.add_column(sa.Column('time_window_end', sa.DateTime, nullable=True))

    # ============================================
    # Step 3: Create config_venue table
    # ============================================
    op.create_table(
        'config_venue',
        sa.Column('venue_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('venue_code', sa.String(50), unique=True, nullable=False),
        sa.Column('venue_name', sa.String(255), nullable=False),
        sa.Column('venue_name_en', sa.String(255), nullable=True),
        sa.Column('openalex_source_id', sa.String(50), unique=True, nullable=True),
        sa.Column('venue_type', sa.String(30), nullable=False, server_default='conference'),
        sa.Column('country_code', sa.String(10), nullable=True),
        sa.Column('publisher', sa.String(100), nullable=True),
        sa.Column('h_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('works_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cited_by_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('last_collect_at', sa.DateTime, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_config_venue_code', 'config_venue', ['venue_code'])
    op.create_index('ix_config_venue_name', 'config_venue', ['venue_name'])
    op.create_index('ix_config_venue_openalex_id', 'config_venue', ['openalex_source_id'])
    op.create_index('ix_config_venue_type', 'config_venue', ['venue_type'])

    # ============================================
    # Step 4: Create config_venue_tech_binding table
    # ============================================
    op.create_table(
        'config_venue_tech_binding',
        sa.Column('binding_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('venue_id', sa.Integer, nullable=False),
        sa.Column('tech_element_id', sa.Integer, nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('collect_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('last_collect_at', sa.DateTime, nullable=True),
        sa.Column('author_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('work_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('venue_id', 'tech_element_id', name='uq_venue_tech_element'),
    )
    op.create_index('ix_venue_binding_venue', 'config_venue_tech_binding', ['venue_id'])
    op.create_index('ix_venue_binding_tech', 'config_venue_tech_binding', ['tech_element_id'])
    op.create_index('ix_venue_binding_status', 'config_venue_tech_binding', ['collect_status'])

    # Add foreign keys
    op.create_foreign_key(
        'fk_venue_binding_venue',
        'config_venue_tech_binding',
        'config_venue',
        ['venue_id'],
        ['venue_id']
    )
    op.create_foreign_key(
        'fk_venue_binding_tech',
        'config_venue_tech_binding',
        'core_tech_element',
        ['tech_element_id'],
        ['tech_element_id']
    )

    # ============================================
    # Step 5: Create sync_venue_sub_task table
    # ============================================
    op.create_table(
        'sync_venue_sub_task',
        sa.Column('sub_task_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.Integer, nullable=False),
        sa.Column('venue_id', sa.Integer, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('time_window_start', sa.DateTime, nullable=True),
        sa.Column('time_window_end', sa.DateTime, nullable=True),
        sa.Column('works_fetched', sa.Integer, nullable=False, server_default='0'),
        sa.Column('authors_fetched', sa.Integer, nullable=False, server_default='0'),
        sa.Column('new_authors', sa.Integer, nullable=False, server_default='0'),
        sa.Column('updated_authors', sa.Integer, nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_venue_sub_task_task', 'sync_venue_sub_task', ['task_id'])
    op.create_index('ix_venue_sub_task_venue', 'sync_venue_sub_task', ['venue_id'])
    op.create_index('ix_venue_sub_task_status', 'sync_venue_sub_task', ['status'])

    # Add foreign keys
    op.create_foreign_key(
        'fk_venue_sub_task_task',
        'sync_venue_sub_task',
        'sync_collect_task',
        ['task_id'],
        ['task_id']
    )
    op.create_foreign_key(
        'fk_venue_sub_task_venue',
        'sync_venue_sub_task',
        'config_venue',
        ['venue_id'],
        ['venue_id']
    )


def downgrade():
    # Drop sync_venue_sub_task
    op.drop_constraint('fk_venue_sub_task_venue', 'sync_venue_sub_task', type_='foreignkey')
    op.drop_constraint('fk_venue_sub_task_task', 'sync_venue_sub_task', type_='foreignkey')
    op.drop_table('sync_venue_sub_task')

    # Drop config_venue_tech_binding
    op.drop_constraint('fk_venue_binding_tech', 'config_venue_tech_binding', type_='foreignkey')
    op.drop_constraint('fk_venue_binding_venue', 'config_venue_tech_binding', type_='foreignkey')
    op.drop_table('config_venue_tech_binding')

    # Drop config_venue
    op.drop_table('config_venue')

    # Drop time_window from sync_collect_task
    with op.batch_alter_table('sync_collect_task', schema=None) as batch_op:
        batch_op.drop_column('time_window_end')
        batch_op.drop_column('time_window_start')

    # Drop is_top_school from core_school
    op.drop_index('ix_core_school_is_top', 'core_school')
    with op.batch_alter_table('core_school', schema=None) as batch_op:
        batch_op.drop_column('is_top_school')
