"""Add JD match tables for v1.4

Revision ID: 027
Revises: 026
Create Date: 2026-04-11

This migration adds JD match session and result tables:
1. jd_match_session: Store JD matching sessions
2. jd_match_result: Store matching results
"""
from alembic import op
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON


# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add JD match tables."""
    # Create JD match session table
    op.create_table(
        'jd_match_session',
        Column('session_id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', Integer, ForeignKey('iam_user_account.user_id'), nullable=False),
        Column('jd_text', Text, nullable=False),
        Column('jd_features', JSON, nullable=True),
        Column('status', String(20), nullable=False, server_default='pending'),
        Column('created_at', DateTime, nullable=False),
        Column('completed_at', DateTime, nullable=True),
    )

    # Create indexes
    op.create_index(
        'ix_jd_match_session_user',
        'jd_match_session',
        ['user_id'],
    )
    op.create_index(
        'ix_jd_match_session_status',
        'jd_match_session',
        ['status'],
    )
    op.create_index(
        'ix_jd_match_session_created',
        'jd_match_session',
        ['created_at'],
    )

    # Create JD match result table
    op.create_table(
        'jd_match_result',
        Column('result_id', Integer, primary_key=True, autoincrement=True),
        Column('session_id', Integer, ForeignKey('jd_match_session.session_id', ondelete='CASCADE'), nullable=False),
        Column('talent_id', Integer, ForeignKey('core_talent.talent_id'), nullable=False),

        # Scores
        Column('overall_score', Float, nullable=True),
        Column('skill_score', Float, nullable=True),
        Column('research_score', Float, nullable=True),
        Column('experience_score', Float, nullable=True),

        # Match details
        Column('match_reasons', JSON, nullable=True),
        Column('highlight_skills', JSON, nullable=True),

        Column('created_at', DateTime, nullable=False),
    )

    # Create indexes
    op.create_index(
        'ix_jd_match_result_session',
        'jd_match_result',
        ['session_id'],
    )
    op.create_index(
        'ix_jd_match_result_talent',
        'jd_match_result',
        ['talent_id'],
    )
    op.create_index(
        'ix_jd_match_result_score',
        'jd_match_result',
        ['overall_score'],
    )


def downgrade() -> None:
    """Remove JD match tables."""
    op.drop_table('jd_match_result')
    op.drop_table('jd_match_session')
