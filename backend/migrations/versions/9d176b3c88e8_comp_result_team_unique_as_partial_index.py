"""comp_result team unique as partial index

The plain (team_id, contest_id) unique constraint wrongly rejected personal
results that carry team_id (multiple members of the same team). Replace it
with a partial unique index applying only to team-owned rows (talent_id
IS NULL).

Revision ID: 9d176b3c88e8
Revises: 60f8cd893264
Create Date: 2026-07-19 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9d176b3c88e8'
down_revision: Union[str, None] = '60f8cd893264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_comp_result_team_contest', 'comp_result', type_='unique')
    op.create_index(
        'uq_comp_result_team_contest',
        'comp_result',
        ['team_id', 'contest_id'],
        unique=True,
        postgresql_where='talent_id IS NULL',
    )


def downgrade() -> None:
    op.drop_index('uq_comp_result_team_contest', table_name='comp_result')
    op.create_unique_constraint('uq_comp_result_team_contest', 'comp_result', ['team_id', 'contest_id'])
