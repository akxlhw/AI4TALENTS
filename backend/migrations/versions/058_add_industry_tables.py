"""Add industry talent domain tables

Revision ID: 058
Revises: 057
Create Date: 2026-08-01

Creates the V5.0.0 industry talent domain table family
(docs/v5.0.0/02-技术设计.md §3):
1. industry_position — recruiting positions (lifecycle via status, no delete)
2. industry_talent — globally unique candidates (dedup_hash unique)
3. industry_position_talent — position-talent link with match scores,
   unique on (position_id, talent_id)
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '058'
down_revision = '057'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the three industry_* tables with indexes and unique constraints."""
    op.create_table(
        'industry_position',
        sa.Column('position_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('tech_direction_codes', sa.JSON(), nullable=True),
        sa.Column('level_min', sa.Integer(), nullable=True),
        sa.Column('level_max', sa.Integer(), nullable=True),
        sa.Column('jd_text', sa.Text(), nullable=True),
        sa.Column('jd_features', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['iam_user_account.user_id']),
        sa.PrimaryKeyConstraint('position_id'),
    )
    op.create_index('ix_industry_position_title', 'industry_position', ['title'])
    op.create_index('ix_industry_position_status', 'industry_position', ['status'])

    op.create_table(
        'industry_talent',
        sa.Column('talent_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('current_org', sa.String(length=255), nullable=True),
        sa.Column('current_title', sa.String(length=255), nullable=True),
        sa.Column('degree', sa.String(length=50), nullable=True),
        sa.Column('years_of_exp', sa.String(length=20), nullable=True),
        sa.Column('years_of_exp_num', sa.Float(), nullable=True),
        sa.Column('experiences', sa.JSON(), nullable=True),
        sa.Column('expect', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('profile_url', sa.String(length=1000), nullable=True),
        sa.Column('photo_url', sa.String(length=1000), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('dedup_hash', sa.String(length=64), nullable=False),
        sa.Column('unified_person_id', sa.String(length=100), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('talent_id'),
        sa.UniqueConstraint('dedup_hash'),
    )
    op.create_index('ix_industry_talent_name', 'industry_talent', ['name'])
    op.create_index('ix_industry_talent_current_org', 'industry_talent', ['current_org'])
    op.create_index('ix_industry_talent_dedup_hash', 'industry_talent', ['dedup_hash'])
    op.create_index(
        'ix_industry_talent_unified_person_id', 'industry_talent', ['unified_person_id']
    )

    op.create_table(
        'industry_position_talent',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('talent_id', sa.Integer(), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('score_school', sa.Float(), nullable=True),
        sa.Column('score_company', sa.Float(), nullable=True),
        sa.Column('score_direction', sa.Float(), nullable=True),
        sa.Column('match_tags', sa.JSON(), nullable=True),
        sa.Column('match_reason', sa.Text(), nullable=True),
        sa.Column('touched', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('batch', sa.String(length=50), nullable=True),
        sa.Column('source_platform', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['industry_position.position_id']),
        sa.ForeignKeyConstraint(['talent_id'], ['industry_talent.talent_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('position_id', 'talent_id', name='uq_industry_position_talent'),
    )
    op.create_index(
        'ix_industry_position_talent_position_id', 'industry_position_talent', ['position_id']
    )
    op.create_index(
        'ix_industry_position_talent_talent_id', 'industry_position_talent', ['talent_id']
    )
    op.create_index('ix_industry_position_talent_status', 'industry_position_talent', ['status'])


def downgrade() -> None:
    """Drop the industry_* table family (children first)."""
    op.drop_index('ix_industry_position_talent_status', table_name='industry_position_talent')
    op.drop_index('ix_industry_position_talent_talent_id', table_name='industry_position_talent')
    op.drop_index(
        'ix_industry_position_talent_position_id', table_name='industry_position_talent'
    )
    op.drop_table('industry_position_talent')
    op.drop_index('ix_industry_talent_unified_person_id', table_name='industry_talent')
    op.drop_index('ix_industry_talent_dedup_hash', table_name='industry_talent')
    op.drop_index('ix_industry_talent_current_org', table_name='industry_talent')
    op.drop_index('ix_industry_talent_name', table_name='industry_talent')
    op.drop_table('industry_talent')
    op.drop_index('ix_industry_position_status', table_name='industry_position')
    op.drop_index('ix_industry_position_title', table_name='industry_position')
    op.drop_table('industry_position')
