"""unify role types

Revision ID: 011
Revises: 010_add_openalex_tables
Create Date: 2026-03-25

统一角色类型枚举：
- 移除 teaching_research (合并到 professor)
- graduated -> graduate (与前端一致)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """统一角色类型枚举值"""
    # 使用 SQLAlchemy 连接执行 SQL
    conn = op.get_bind()

    # 1. 将 graduated 改为 graduate
    conn.execute(
        sa.text("UPDATE core_talent SET role_type = 'graduate' WHERE role_type = 'graduated'")
    )

    # 2. 将 teaching_research 改为 professor
    conn.execute(
        sa.text("UPDATE core_talent SET role_type = 'professor' WHERE role_type = 'teaching_research'")
    )

    # 3. 将其他不在合法枚举范围内的类型改为 unknown
    conn.execute(
        sa.text("""
            UPDATE core_talent
            SET role_type = 'unknown'
            WHERE role_type NOT IN ('professor', 'student', 'graduate', 'unknown')
        """)
    )

    # 4. 同步更新 core_role_profile 表 (如果存在)
    try:
        conn.execute(
            sa.text("UPDATE core_role_profile SET role_type = 'graduate' WHERE role_type = 'graduated'")
        )
        conn.execute(
            sa.text("UPDATE core_role_profile SET role_type = 'professor' WHERE role_type = 'teaching_research'")
        )
        conn.execute(
            sa.text("""
                UPDATE core_role_profile
                SET role_type = 'unknown'
                WHERE role_type NOT IN ('professor', 'student', 'graduate', 'unknown')
            """)
        )
    except Exception as e:
        # 表可能不存在，忽略错误
        print(f"Note: core_role_profile table update skipped: {e}")

    print("Role types unified successfully.")


def downgrade() -> None:
    """回滚角色类型变更"""
    conn = op.get_bind()

    # 回滚：graduate -> graduated
    conn.execute(
        sa.text("UPDATE core_talent SET role_type = 'graduated' WHERE role_type = 'graduate'")
    )

    # 注意：无法精确区分哪些 professor 原本是 teaching_research
    # 这是单向迁移，无法完全回滚

    print("Warning: Downgrade is partial. Some role type mappings cannot be reversed.")
