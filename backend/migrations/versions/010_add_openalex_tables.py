"""Add OpenAlex entity tables

Revision ID: 010
Revises: 009
Create Date: 2026-03-25

添加 OpenAlex 完整数据实体表：
- openalex_author: 作者
- openalex_work: 作品/论文
- openalex_source: 期刊/会议
- openalex_institution: 机构
- openalex_concept: 概念/研究领域
- openalex_publisher: 出版商
- openalex_funder: 资助机构
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON

# revision identifiers
revision = '010'
down_revision = '009_simplify_collect_config'
branch_labels = None
depends_on = None


def upgrade():
    # OpenAlex Author 表
    op.create_table(
        'openalex_author',
        sa.Column('author_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('display_name_alternatives', JSON),
        sa.Column('orcid', sa.String(50)),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('h_index', sa.Integer, default=0),
        sa.Column('i10_index', sa.Integer, default=0),
        sa.Column('institution_ids', JSON),
        sa.Column('last_known_institution', sa.String(500)),
        sa.Column('topics', JSON),
        sa.Column('x_concepts', JSON),
        sa.Column('counts_by_year', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_openalex_author_name', 'openalex_author', ['display_name'])
    op.create_index('ix_openalex_author_orcid', 'openalex_author', ['orcid'])
    op.create_index('ix_openalex_author_works', 'openalex_author', ['works_count'])

    # OpenAlex Work 表
    op.create_table(
        'openalex_work',
        sa.Column('work_id', sa.String(50), primary_key=True),
        sa.Column('title', sa.Text),
        sa.Column('display_name', sa.Text),
        sa.Column('doi', sa.String(200)),
        sa.Column('publication_year', sa.Integer),
        sa.Column('publication_date', sa.String(20)),
        sa.Column('type', sa.String(50)),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('is_retracted', sa.Integer, default=0),
        sa.Column('is_paratext', sa.Integer, default=0),
        sa.Column('language', sa.String(10)),
        sa.Column('source_id', sa.String(50)),
        sa.Column('source_name', sa.String(500)),
        sa.Column('author_count', sa.Integer, default=0),
        sa.Column('author_ids', JSON),
        sa.Column('institution_ids', JSON),
        sa.Column('concepts', JSON),
        sa.Column('keywords', JSON),
        sa.Column('referenced_works', JSON),
        sa.Column('related_works', JSON),
        sa.Column('abstract_inverted_index', JSON),
        sa.Column('open_access', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_openalex_work_title', 'openalex_work', ['title'])
    op.create_index('ix_openalex_work_doi', 'openalex_work', ['doi'])
    op.create_index('ix_openalex_work_year', 'openalex_work', ['publication_year'])
    op.create_index('ix_openalex_work_source', 'openalex_work', ['source_id'])
    op.create_index('ix_openalex_work_type', 'openalex_work', ['type'])

    # OpenAlex Source (期刊/会议) 表
    op.create_table(
        'openalex_source',
        sa.Column('source_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('type', sa.String(50)),
        sa.Column('issn', JSON),
        sa.Column('issn_l', sa.String(20)),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('h_index', sa.Integer, default=0),
        sa.Column('is_oa', sa.Integer, default=0),
        sa.Column('is_in_doaj', sa.Integer, default=0),
        sa.Column('host_organization', sa.String(500)),
        sa.Column('host_organization_id', sa.String(50)),
        sa.Column('country_codes', JSON),
        sa.Column('apc_prices', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_openalex_source_name', 'openalex_source', ['display_name'])
    op.create_index('ix_openalex_source_type', 'openalex_source', ['type'])
    op.create_index('ix_openalex_source_issn', 'openalex_source', ['issn_l'])

    # OpenAlex Institution 表
    op.create_table(
        'openalex_institution',
        sa.Column('institution_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('display_name_alternatives', JSON),
        sa.Column('country_code', sa.String(10)),
        sa.Column('country_name', sa.String(100)),
        sa.Column('type', sa.String(50)),
        sa.Column('ror', sa.String(50)),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('h_index', sa.Integer, default=0),
        sa.Column('homepage_url', sa.String(500)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('latitude', sa.Float),
        sa.Column('longitude', sa.Float),
        sa.Column('geo', JSON),
        sa.Column('associated_institutions', JSON),
        sa.Column('counts_by_year', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_openalex_inst_name', 'openalex_institution', ['display_name'])
    op.create_index('ix_openalex_inst_country', 'openalex_institution', ['country_code'])
    op.create_index('ix_openalex_inst_type', 'openalex_institution', ['type'])

    # OpenAlex Concept 表
    op.create_table(
        'openalex_concept',
        sa.Column('concept_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('level', sa.Integer),
        sa.Column('description', sa.Text),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('wikidata', sa.String(100)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('ancestors', JSON),
        sa.Column('related_concepts', JSON),
        sa.Column('counts_by_year', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_openalex_concept_name', 'openalex_concept', ['display_name'])
    op.create_index('ix_openalex_concept_level', 'openalex_concept', ['level'])

    # OpenAlex Publisher 表
    op.create_table(
        'openalex_publisher',
        sa.Column('publisher_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('alternate_titles', JSON),
        sa.Column('hierarchy_level', sa.Integer),
        sa.Column('parent_publisher', sa.String(50)),
        sa.Column('country_codes', JSON),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('h_index', sa.Integer, default=0),
        sa.Column('homepage_url', sa.String(500)),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # OpenAlex Funder 表
    op.create_table(
        'openalex_funder',
        sa.Column('funder_id', sa.String(50), primary_key=True),
        sa.Column('display_name', sa.String(500)),
        sa.Column('alternate_titles', JSON),
        sa.Column('country_code', sa.String(10)),
        sa.Column('description', sa.Text),
        sa.Column('works_count', sa.Integer, default=0),
        sa.Column('cited_by_count', sa.Integer, default=0),
        sa.Column('awards_count', sa.Integer, default=0),
        sa.Column('homepage_url', sa.String(500)),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 作品-作者关联表 (用于快速查询)
    op.create_table(
        'openalex_work_author',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('work_id', sa.String(50), nullable=False),
        sa.Column('author_id', sa.String(50), nullable=False),
        sa.Column('author_position', sa.String(20)),
        sa.Column('is_corresponding', sa.Integer, default=0),
        sa.Column('affiliation_raw', sa.String(500)),
        sa.Column('affiliation_id', sa.String(50)),
    )
    op.create_index('ix_work_author_work', 'openalex_work_author', ['work_id'])
    op.create_index('ix_work_author_author', 'openalex_work_author', ['author_id'])

    # 作品-概念关联表
    op.create_table(
        'openalex_work_concept',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('work_id', sa.String(50), nullable=False),
        sa.Column('concept_id', sa.String(50), nullable=False),
        sa.Column('score', sa.Float),
    )
    op.create_index('ix_work_concept_work', 'openalex_work_concept', ['work_id'])
    op.create_index('ix_work_concept_concept', 'openalex_work_concept', ['concept_id'])


def downgrade():
    op.drop_table('openalex_work_concept')
    op.drop_table('openalex_work_author')
    op.drop_table('openalex_funder')
    op.drop_table('openalex_publisher')
    op.drop_table('openalex_concept')
    op.drop_table('openalex_institution')
    op.drop_table('openalex_source')
    op.drop_table('openalex_work')
    op.drop_table('openalex_author')
