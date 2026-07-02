"""add_lab_talent_table

Revision ID: 050_add_lab_talent_table
Revises: 049_add_genealogy_tables
Create Date: 2026-07-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '050_add_lab_talent_table'
down_revision: Union[str, None] = '049_add_genealogy_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_talent',
        sa.Column('talent_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role_section', sa.String(length=100), nullable=False),
        sa.Column('role_type', sa.String(length=20), nullable=False, server_default='unknown'),
        sa.Column('academic_level', sa.String(length=20), nullable=True),
        sa.Column('current_title', sa.String(length=255), nullable=True),
        sa.Column('homepage', sa.String(length=500), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('research_areas', sa.JSON(), nullable=True),
        sa.Column('cohort_year', sa.Integer(), nullable=True),
        sa.Column('cohort_source', sa.String(length=255), nullable=True),
        sa.Column('lab_name', sa.String(length=255), nullable=False),
        sa.Column('parent_lab', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('source_detail_url', sa.String(length=1000), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=True),
        sa.Column('dedup_hash', sa.String(length=64), nullable=False),
        sa.Column('unified_person_id', sa.String(length=100), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('talent_id'),
        sa.UniqueConstraint('dedup_hash', name='uq_lab_talent_dedup_hash'),
    )
    op.create_index('ix_lab_talent_talent_id', 'lab_talent', ['talent_id'], unique=False)
    op.create_index('ix_lab_talent_name', 'lab_talent', ['name'], unique=False)
    op.create_index('ix_lab_talent_role_type', 'lab_talent', ['role_type'], unique=False)
    op.create_index('ix_lab_talent_academic_level', 'lab_talent', ['academic_level'], unique=False)
    op.create_index('ix_lab_talent_cohort_year', 'lab_talent', ['cohort_year'], unique=False)
    op.create_index('ix_lab_talent_lab_name', 'lab_talent', ['lab_name'], unique=False)
    op.create_index('ix_lab_talent_parent_lab', 'lab_talent', ['parent_lab'], unique=False)
    op.create_index('ix_lab_talent_dedup_hash', 'lab_talent', ['dedup_hash'], unique=True)
    op.create_index('ix_lab_talent_unified_person_id', 'lab_talent', ['unified_person_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_lab_talent_unified_person_id', table_name='lab_talent')
    op.drop_index('ix_lab_talent_dedup_hash', table_name='lab_talent')
    op.drop_index('ix_lab_talent_parent_lab', table_name='lab_talent')
    op.drop_index('ix_lab_talent_lab_name', table_name='lab_talent')
    op.drop_index('ix_lab_talent_cohort_year', table_name='lab_talent')
    op.drop_index('ix_lab_talent_academic_level', table_name='lab_talent')
    op.drop_index('ix_lab_talent_role_type', table_name='lab_talent')
    op.drop_index('ix_lab_talent_name', table_name='lab_talent')
    op.drop_index('ix_lab_talent_talent_id', table_name='lab_talent')
    op.drop_table('lab_talent')
