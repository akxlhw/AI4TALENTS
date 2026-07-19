"""add competition domain tables

Revision ID: 60f8cd893264
Revises: 054_add_social_links
Create Date: 2026-07-19 11:08:22.961838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60f8cd893264'
down_revision: Union[str, None] = '054_add_social_links'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comp_series',
        sa.Column('series_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_en', sa.String(length=255), nullable=True),
        sa.Column('homepage', sa.String(length=500), nullable=True),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('logo_url', sa.String(length=1000), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('series_id'),
    )
    op.create_index('ix_comp_series_code', 'comp_series', ['code'], unique=True)

    op.create_table(
        'comp_contest',
        sa.Column('contest_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('series_id', sa.Integer(), nullable=False),
        sa.Column('source_code', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('season', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='finished'),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('raw_meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['series_id'], ['comp_series.series_id']),
        sa.PrimaryKeyConstraint('contest_id'),
        sa.UniqueConstraint('source_code', 'external_id', name='uq_comp_contest_source_external'),
    )
    op.create_index('ix_comp_contest_series_id', 'comp_contest', ['series_id'], unique=False)
    op.create_index('ix_comp_contest_source_code', 'comp_contest', ['source_code'], unique=False)
    op.create_index('ix_comp_contest_start_time', 'comp_contest', ['start_time'], unique=False)
    op.create_index('ix_comp_contest_season', 'comp_contest', ['season'], unique=False)

    op.create_table(
        'comp_talent',
        sa.Column('talent_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('handle', sa.String(length=255), nullable=False),
        sa.Column('handle_lower', sa.String(length=255), nullable=False),
        sa.Column('source_code', sa.String(length=50), nullable=False),
        sa.Column('real_name', sa.String(length=255), nullable=True),
        sa.Column('school', sa.String(length=255), nullable=True),
        sa.Column('country_code', sa.String(length=10), nullable=True),
        sa.Column('avatar_url', sa.String(length=1000), nullable=True),
        sa.Column('profile_url', sa.String(length=1000), nullable=True),
        sa.Column('current_rating', sa.Integer(), nullable=True),
        sa.Column('max_rating', sa.Integer(), nullable=True),
        sa.Column('rank_title', sa.String(length=50), nullable=True),
        sa.Column('global_rank', sa.Integer(), nullable=True),
        sa.Column('contests_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medals_gold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medals_silver', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medals_bronze', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('specialties', sa.JSON(), nullable=True),
        sa.Column('last_contest_at', sa.DateTime(), nullable=True),
        sa.Column('dedup_hash', sa.String(length=64), nullable=False),
        sa.Column('unified_person_id', sa.String(length=100), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('talent_id'),
        sa.UniqueConstraint('source_code', 'handle_lower', name='uq_comp_talent_source_handle'),
    )
    op.create_index('ix_comp_talent_talent_id', 'comp_talent', ['talent_id'], unique=False)
    op.create_index('ix_comp_talent_handle', 'comp_talent', ['handle'], unique=False)
    op.create_index('ix_comp_talent_handle_lower', 'comp_talent', ['handle_lower'], unique=False)
    op.create_index('ix_comp_talent_source_code', 'comp_talent', ['source_code'], unique=False)
    op.create_index('ix_comp_talent_school', 'comp_talent', ['school'], unique=False)
    op.create_index('ix_comp_talent_country_code', 'comp_talent', ['country_code'], unique=False)
    op.create_index('ix_comp_talent_current_rating', 'comp_talent', ['current_rating'], unique=False)
    op.create_index('ix_comp_talent_rank_title', 'comp_talent', ['rank_title'], unique=False)
    op.create_index('ix_comp_talent_last_contest_at', 'comp_talent', ['last_contest_at'], unique=False)
    op.create_index('ix_comp_talent_dedup_hash', 'comp_talent', ['dedup_hash'], unique=True)
    op.create_index('ix_comp_talent_unified_person_id', 'comp_talent', ['unified_person_id'], unique=False)

    op.create_table(
        'comp_team',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_lower', sa.String(length=255), nullable=False),
        sa.Column('school', sa.String(length=255), nullable=True),
        sa.Column('country_code', sa.String(length=10), nullable=True),
        sa.Column('logo_url', sa.String(length=1000), nullable=True),
        sa.Column('dedup_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('team_id'),
        sa.UniqueConstraint('source_code', 'name_lower', 'school', name='uq_comp_team_identity'),
    )
    op.create_index('ix_comp_team_source_code', 'comp_team', ['source_code'], unique=False)
    op.create_index('ix_comp_team_name_lower', 'comp_team', ['name_lower'], unique=False)
    op.create_index('ix_comp_team_school', 'comp_team', ['school'], unique=False)
    op.create_index('ix_comp_team_country_code', 'comp_team', ['country_code'], unique=False)
    op.create_index('ix_comp_team_dedup_hash', 'comp_team', ['dedup_hash'], unique=True)

    op.create_table(
        'comp_result',
        sa.Column('result_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('talent_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('rating_before', sa.Integer(), nullable=True),
        sa.Column('rating_after', sa.Integer(), nullable=True),
        sa.Column('award', sa.String(length=20), nullable=True),
        sa.Column('team_name', sa.String(length=255), nullable=True),
        sa.Column('team_members', sa.JSON(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('raw_meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint(
            'talent_id IS NOT NULL OR team_id IS NOT NULL',
            name='ck_comp_result_has_owner',
        ),
        sa.ForeignKeyConstraint(['contest_id'], ['comp_contest.contest_id']),
        sa.ForeignKeyConstraint(['talent_id'], ['comp_talent.talent_id']),
        sa.ForeignKeyConstraint(['team_id'], ['comp_team.team_id']),
        sa.PrimaryKeyConstraint('result_id'),
        sa.UniqueConstraint('talent_id', 'contest_id', name='uq_comp_result_talent_contest'),
        sa.UniqueConstraint('team_id', 'contest_id', name='uq_comp_result_team_contest'),
    )
    op.create_index('ix_comp_result_talent_id', 'comp_result', ['talent_id'], unique=False)
    op.create_index('ix_comp_result_team_id', 'comp_result', ['team_id'], unique=False)
    op.create_index('ix_comp_result_contest_id', 'comp_result', ['contest_id'], unique=False)
    op.create_index('ix_comp_result_award', 'comp_result', ['award'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_comp_result_award', table_name='comp_result')
    op.drop_index('ix_comp_result_contest_id', table_name='comp_result')
    op.drop_index('ix_comp_result_team_id', table_name='comp_result')
    op.drop_index('ix_comp_result_talent_id', table_name='comp_result')
    op.drop_table('comp_result')
    op.drop_index('ix_comp_team_dedup_hash', table_name='comp_team')
    op.drop_index('ix_comp_team_country_code', table_name='comp_team')
    op.drop_index('ix_comp_team_school', table_name='comp_team')
    op.drop_index('ix_comp_team_name_lower', table_name='comp_team')
    op.drop_index('ix_comp_team_source_code', table_name='comp_team')
    op.drop_table('comp_team')
    op.drop_index('ix_comp_talent_unified_person_id', table_name='comp_talent')
    op.drop_index('ix_comp_talent_dedup_hash', table_name='comp_talent')
    op.drop_index('ix_comp_talent_last_contest_at', table_name='comp_talent')
    op.drop_index('ix_comp_talent_rank_title', table_name='comp_talent')
    op.drop_index('ix_comp_talent_current_rating', table_name='comp_talent')
    op.drop_index('ix_comp_talent_country_code', table_name='comp_talent')
    op.drop_index('ix_comp_talent_school', table_name='comp_talent')
    op.drop_index('ix_comp_talent_source_code', table_name='comp_talent')
    op.drop_index('ix_comp_talent_handle_lower', table_name='comp_talent')
    op.drop_index('ix_comp_talent_handle', table_name='comp_talent')
    op.drop_index('ix_comp_talent_talent_id', table_name='comp_talent')
    op.drop_table('comp_talent')
    op.drop_index('ix_comp_contest_season', table_name='comp_contest')
    op.drop_index('ix_comp_contest_start_time', table_name='comp_contest')
    op.drop_index('ix_comp_contest_source_code', table_name='comp_contest')
    op.drop_index('ix_comp_contest_series_id', table_name='comp_contest')
    op.drop_table('comp_contest')
    op.drop_index('ix_comp_series_code', table_name='comp_series')
    op.drop_table('comp_series')
