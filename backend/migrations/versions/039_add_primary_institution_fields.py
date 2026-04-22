"""Add primary institution fields for education and company separation

Revision ID: 039
Revises: 038
Create Date: 2026-04-22

将机构信息分为教育机构和公司机构两类，解决以下问题：
1. 当前 last_known_institutions[0] 不一定是主要学术机构
2. OpenAlex 的 last_known_institutions 可能为 None
3. 没有区分机构类型（教育机构 vs 公司机构）

选择策略：按 affiliations.years 数量排序，选择发文最多的机构
"""
from alembic import op
import sqlalchemy as sa


revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加主要机构字段"""

    # 1. RawAuthor 表新增字段
    op.add_column('raw_author', sa.Column('primary_education_id', sa.String(50), nullable=True))
    op.add_column('raw_author', sa.Column('primary_education_name', sa.String(255), nullable=True))
    op.add_column('raw_author', sa.Column('primary_company_id', sa.String(50), nullable=True))
    op.add_column('raw_author', sa.Column('primary_company_name', sa.String(255), nullable=True))

    # 2. StdAuthor 表新增字段
    op.add_column('std_author', sa.Column('primary_education_id', sa.String(50), nullable=True))
    op.add_column('std_author', sa.Column('primary_education_name', sa.String(255), nullable=True))
    op.add_column('std_author', sa.Column('primary_company_id', sa.String(50), nullable=True))
    op.add_column('std_author', sa.Column('primary_company_name', sa.String(255), nullable=True))

    # 3. Talent 表新增字段（外键关联 core_school）
    op.add_column('core_talent', sa.Column('education_school_id', sa.Integer, nullable=True))
    op.add_column('core_talent', sa.Column('company_school_id', sa.Integer, nullable=True))

    # 4. 添加外键约束
    op.create_foreign_key(
        'fk_talent_education_school',
        'core_talent',
        'core_school',
        ['education_school_id'],
        ['school_id']
    )
    op.create_foreign_key(
        'fk_talent_company_school',
        'core_talent',
        'core_school',
        ['company_school_id'],
        ['school_id']
    )

    # 5. 添加索引
    op.create_index('ix_talent_education_school', 'core_talent', ['education_school_id'])
    op.create_index('ix_talent_company_school', 'core_talent', ['company_school_id'])


def downgrade() -> None:
    """回滚：删除主要机构字段"""

    # 1. 删除 Talent 表索引和字段
    op.drop_index('ix_talent_company_school', 'core_talent')
    op.drop_index('ix_talent_education_school', 'core_talent')

    op.drop_constraint('fk_talent_company_school', 'core_talent', type_='foreignkey')
    op.drop_constraint('fk_talent_education_school', 'core_talent', type_='foreignkey')

    op.drop_column('core_talent', 'company_school_id')
    op.drop_column('core_talent', 'education_school_id')

    # 2. 删除 StdAuthor 表字段
    op.drop_column('std_author', 'primary_company_name')
    op.drop_column('std_author', 'primary_company_id')
    op.drop_column('std_author', 'primary_education_name')
    op.drop_column('std_author', 'primary_education_id')

    # 3. 删除 RawAuthor 表字段
    op.drop_column('raw_author', 'primary_company_name')
    op.drop_column('raw_author', 'primary_company_id')
    op.drop_column('raw_author', 'primary_education_name')
    op.drop_column('raw_author', 'primary_education_id')
