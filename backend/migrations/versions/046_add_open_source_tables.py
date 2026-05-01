"""Add open source talent tables

Revision ID: 046
Revises: 045_update_search_text_with_openalex_topics
Create Date: 2026-04-30

This migration:
1. Creates 12 core open source tables (os_* prefix)
2. Creates IAM tables for open source favorites and talent pools
3. Adds performance indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # os_repo_config
    op.create_table(
        'os_repo_config',
        sa.Column('repo_config_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo_full_name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tech_element', sa.String(length=50), nullable=False),
        sa.Column('tech_direction_id', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('stars_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('collect_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['iam_user_account.user_id'], ),
        sa.ForeignKeyConstraint(['tech_direction_id'], ['core_tech_direction.tech_direction_id'], ),
        sa.PrimaryKeyConstraint('repo_config_id')
    )
    op.create_index('ix_os_repo_config_repo_full_name', 'os_repo_config', ['repo_full_name'], unique=True)
    op.create_index('ix_os_repo_config_active_element', 'os_repo_config', ['is_active', 'tech_element'], unique=False)
    op.create_index('ix_os_repo_config_collect', 'os_repo_config', ['is_active', 'collect_enabled'], unique=False)

    # os_developer
    op.create_table(
        'os_developer',
        sa.Column('developer_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('github_login', sa.String(length=100), nullable=False),
        sa.Column('github_id', sa.BigInteger(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('blog_url', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('followers_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('following_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('public_repos_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_stars_received', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_forks_received', sa.Integer(), server_default='0', nullable=False),
        sa.Column('primary_languages', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('tech_tags', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('is_visible', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('developer_id')
    )
    op.create_index('ix_os_developer_github_login', 'os_developer', ['github_login'], unique=True)
    op.create_index('ix_os_developer_visible', 'os_developer', ['is_visible'], unique=False)
    op.create_index('ix_os_developer_stars_desc', 'os_developer', [sa.text('total_stars_received DESC')], unique=False)
    op.create_index('ix_os_developer_company', 'os_developer', ['company'], unique=False)
    op.create_index('ix_os_developer_location', 'os_developer', ['location'], unique=False)

    # os_repository
    op.create_table(
        'os_repository',
        sa.Column('repo_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('github_repo_id', sa.BigInteger(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('stars_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('forks_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('topics', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('is_fork', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.PrimaryKeyConstraint('repo_id')
    )
    op.create_index('ix_os_repository_dev_id', 'os_repository', ['developer_id'], unique=False)
    op.create_index('ix_os_repository_github_id', 'os_repository', ['github_repo_id'], unique=False)
    op.create_index('ix_os_repository_stars', 'os_repository', [sa.text('stars_count DESC')], unique=False)
    op.create_index('ix_os_repository_language', 'os_repository', ['language'], unique=False)
    op.create_index('ix_os_repository_full_name', 'os_repository', ['full_name'], unique=True)

    # os_contribution
    op.create_table(
        'os_contribution',
        sa.Column('contribution_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('repo_id', sa.Integer(), nullable=False),
        sa.Column('commits_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('prs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('issues_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('code_reviews_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_owner', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_maintainer', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.ForeignKeyConstraint(['repo_id'], ['os_repository.repo_id'], ),
        sa.PrimaryKeyConstraint('contribution_id')
    )
    op.create_index('ix_os_contribution_dev_repo', 'os_contribution', ['developer_id', 'repo_id'], unique=True)
    op.create_index('ix_os_contribution_dev_id', 'os_contribution', ['developer_id'], unique=False)

    # os_language_skill
    op.create_table(
        'os_language_skill',
        sa.Column('skill_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('repo_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_commits', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_lines_added', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_lines_deleted', sa.Integer(), server_default='0', nullable=False),
        sa.Column('proficiency_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.PrimaryKeyConstraint('skill_id')
    )
    op.create_index('ix_os_language_skill_dev_id', 'os_language_skill', ['developer_id'], unique=False)
    op.create_index('ix_os_language_skill_dev_lang', 'os_language_skill', ['developer_id', 'language'], unique=True)

    # os_embedding
    op.create_table(
        'os_embedding',
        sa.Column('embedding_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('vector_type', sa.String(length=20), server_default='profile', nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('model_name', sa.String(length=50), nullable=True),
        sa.Column('source_text_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.PrimaryKeyConstraint('embedding_id')
    )
    op.create_index('ix_os_embedding_dev_type', 'os_embedding', ['developer_id', 'vector_type'], unique=True)
    op.create_index('ix_os_embedding_hash', 'os_embedding', ['source_text_hash'], unique=False)

    # os_favourite
    op.create_table(
        'os_favourite',
        sa.Column('favourite_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('followup_status', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['iam_user_account.user_id'], ),
        sa.PrimaryKeyConstraint('favourite_id')
    )
    op.create_index('ix_os_favourite_user_dev', 'os_favourite', ['user_id', 'developer_id'], unique=True)
    op.create_index('ix_os_favourite_user_id', 'os_favourite', ['user_id'], unique=False)

    # os_talent_pool
    op.create_table(
        'os_talent_pool',
        sa.Column('pool_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('pool_name', sa.String(length=255), nullable=False),
        sa.Column('pool_type', sa.String(length=50), nullable=True),
        sa.Column('scope_desc', sa.Text(), nullable=True),
        sa.Column('pool_status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['iam_user_account.user_id'], ),
        sa.PrimaryKeyConstraint('pool_id')
    )
    op.create_index('ix_os_talent_pool_owner', 'os_talent_pool', ['owner_user_id'], unique=False)

    # os_pool_member
    op.create_table(
        'os_pool_member',
        sa.Column('pool_member_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pool_id', sa.Integer(), nullable=False),
        sa.Column('developer_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['os_developer.developer_id'], ),
        sa.ForeignKeyConstraint(['pool_id'], ['os_talent_pool.pool_id'], ),
        sa.PrimaryKeyConstraint('pool_member_id')
    )
    op.create_index('ix_os_pool_member_pool_dev', 'os_pool_member', ['pool_id', 'developer_id'], unique=True)

    # os_collect_task
    op.create_table(
        'os_collect_task',
        sa.Column('task_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('progress_percent', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('total_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('processed_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('config_json', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['iam_user_account.user_id'], ),
        sa.PrimaryKeyConstraint('task_id')
    )
    op.create_index('ix_os_collect_task_status', 'os_collect_task', ['status'], unique=False)
    op.create_index('ix_os_collect_task_created_at', 'os_collect_task', [sa.text('created_at DESC')], unique=False)

    # os_raw_developer
    op.create_table(
        'os_raw_developer',
        sa.Column('raw_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('github_login', sa.String(length=100), nullable=False),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('raw_id')
    )
    op.create_index('ix_os_raw_developer_login', 'os_raw_developer', ['github_login'], unique=False)

    # os_repo_mapping
    op.create_table(
        'os_repo_mapping',
        sa.Column('mapping_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo_full_name', sa.String(length=255), nullable=False),
        sa.Column('tech_direction_id', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tech_direction_id'], ['core_tech_direction.tech_direction_id'], ),
        sa.PrimaryKeyConstraint('mapping_id')
    )
    op.create_index('ix_os_repo_mapping_repo', 'os_repo_mapping', ['repo_full_name'], unique=False)


def downgrade() -> None:
    op.drop_table('os_repo_mapping')
    op.drop_table('os_raw_developer')
    op.drop_table('os_collect_task')
    op.drop_table('os_pool_member')
    op.drop_table('os_talent_pool')
    op.drop_table('os_favourite')
    op.drop_table('os_embedding')
    op.drop_table('os_language_skill')
    op.drop_table('os_contribution')
    op.drop_table('os_repository')
    op.drop_table('os_developer')
    op.drop_table('os_repo_config')
