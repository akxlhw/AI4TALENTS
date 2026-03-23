"""Add tech_element tables

Revision ID: 004_add_tech_element
Revises: 003_add_collaboration
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_tech_element'
down_revision: Union[str, None] = '003_add_collaboration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create core_tech_element table
    op.create_table(
        'core_tech_element',
        sa.Column('tech_element_id', sa.Integer(), primary_key=True),
        sa.Column('element_code', sa.String(50), unique=True, nullable=False),
        sa.Column('element_name', sa.String(100), nullable=False),
        sa.Column('element_name_en', sa.String(100), nullable=True),
        sa.Column('element_desc', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for tech_element
    op.create_index('ix_tech_element_code', 'core_tech_element', ['element_code'])
    op.create_index('ix_tech_element_enabled', 'core_tech_element', ['is_enabled'])

    # Create core_tech_direction table
    op.create_table(
        'core_tech_direction',
        sa.Column('tech_direction_id', sa.Integer(), primary_key=True),
        sa.Column('direction_code', sa.String(50), unique=True, nullable=False),
        sa.Column('direction_name', sa.String(100), nullable=False),
        sa.Column('direction_name_en', sa.String(100), nullable=True),
        sa.Column('tech_element_id', sa.Integer(), sa.ForeignKey('core_tech_element.tech_element_id'), nullable=False),
        sa.Column('direction_desc', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for tech_direction
    op.create_index('ix_tech_direction_code', 'core_tech_direction', ['direction_code'])
    op.create_index('ix_tech_direction_element', 'core_tech_direction', ['tech_element_id'])
    op.create_index('ix_tech_direction_enabled', 'core_tech_direction', ['is_enabled'])

    # Create core_talent_tech_tag table
    op.create_table(
        'core_talent_tech_tag',
        sa.Column('tag_id', sa.Integer(), primary_key=True),
        sa.Column('talent_id', sa.Integer(), sa.ForeignKey('core_talent.talent_id'), nullable=False),
        sa.Column('tech_element_id', sa.Integer(), sa.ForeignKey('core_tech_element.tech_element_id'), nullable=False),
        sa.Column('tech_direction_id', sa.Integer(), sa.ForeignKey('core_tech_direction.tech_direction_id'), nullable=False),
        sa.Column('tag_level', sa.String(20), default='primary', nullable=False),
        sa.Column('tag_source', sa.String(20), default='auto_mapping', nullable=False),
        sa.Column('confirm_status', sa.String(20), default='auto_identified', nullable=False),
        sa.Column('confidence_score', sa.Float(), default=0.8),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('talent_id', 'tech_direction_id', name='uq_talent_tech_direction'),
    )

    # Create indexes for talent_tech_tag
    op.create_index('ix_talent_tech_tag_talent', 'core_talent_tech_tag', ['talent_id'])
    op.create_index('ix_talent_tech_tag_element', 'core_talent_tech_tag', ['tech_element_id'])
    op.create_index('ix_talent_tech_tag_direction', 'core_talent_tech_tag', ['tech_direction_id'])
    op.create_index('ix_talent_tech_tag_enabled', 'core_talent_tech_tag', ['is_enabled'])


def downgrade() -> None:
    op.drop_table('core_talent_tech_tag')
    op.drop_table('core_tech_direction')
    op.drop_table('core_tech_element')
