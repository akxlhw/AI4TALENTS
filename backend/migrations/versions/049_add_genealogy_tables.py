"""add_genealogy_tables

Revision ID: 049_add_genealogy_tables
Revises: 1c4fcce9cd43
Create Date: 2026-06-07 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '049_add_genealogy_tables'
down_revision: Union[str, None] = '1c4fcce9cd43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'genealogy_edge',
        sa.Column('edge_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('from_talent_id', sa.Integer(), nullable=False),
        sa.Column('to_talent_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shared_institution', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('first_year', sa.Integer(), nullable=True),
        sa.Column('last_year', sa.Integer(), nullable=True),
        sa.Column('source_work_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['from_talent_id'], ['core_talent.talent_id']),
        sa.ForeignKeyConstraint(['to_talent_id'], ['core_talent.talent_id']),
        sa.PrimaryKeyConstraint('edge_id'),
        sa.UniqueConstraint('from_talent_id', 'to_talent_id', 'relationship_type', name='uq_genealogy_pair')
    )
    op.create_index('ix_genealogy_edge_from_talent_id', 'genealogy_edge', ['from_talent_id'], unique=False)
    op.create_index('ix_genealogy_edge_to_talent_id', 'genealogy_edge', ['to_talent_id'], unique=False)
    op.create_index('ix_genealogy_edge_relationship_type', 'genealogy_edge', ['relationship_type'], unique=False)
    op.create_index('ix_genealogy_edge_confidence', 'genealogy_edge', ['confidence_score'], unique=False)

    op.create_table(
        'talent_influence_score',
        sa.Column('talent_id', sa.Integer(), nullable=False),
        sa.Column('h_index_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('citation_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('works_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('collaboration_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('bridge_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('composite_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tier', sa.String(length=10), nullable=False, server_default='tier4'),
        sa.Column('is_root', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('computed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['talent_id'], ['core_talent.talent_id']),
        sa.PrimaryKeyConstraint('talent_id')
    )


def downgrade() -> None:
    op.drop_table('talent_influence_score')
    op.drop_index('ix_genealogy_edge_confidence', table_name='genealogy_edge')
    op.drop_index('ix_genealogy_edge_relationship_type', table_name='genealogy_edge')
    op.drop_index('ix_genealogy_edge_to_talent_id', table_name='genealogy_edge')
    op.drop_index('ix_genealogy_edge_from_talent_id', table_name='genealogy_edge')
    op.drop_table('genealogy_edge')
