"""rename tech_element to tech_domain

Revision ID: 038
Revises: 037
Create Date: 2026-04-22

将技术要素重命名为技术领域，为后续扩展预留命名空间：
- 表名: core_tech_element → core_tech_domain
- 主键: tech_element_id → tech_domain_id
- 外键: 所有表中的 tech_element_id → tech_domain_id
"""
from alembic import op
import sqlalchemy as sa


revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """重命名技术要素为技术领域"""

    # 1. 重命名主表
    op.rename_table("core_tech_element", "core_tech_domain")

    # 2. 重命名主键列
    op.alter_column("core_tech_domain", "tech_element_id", new_column_name="tech_domain_id")

    # 2.1 重命名其他字段
    op.alter_column("core_tech_domain", "element_code", new_column_name="domain_code")
    op.alter_column("core_tech_domain", "element_name", new_column_name="domain_name")
    op.alter_column("core_tech_domain", "element_name_en", new_column_name="domain_name_en")
    op.alter_column("core_tech_domain", "element_desc", new_column_name="domain_desc")

    # 3. 重命名外键列 - core_tech_direction
    op.alter_column("core_tech_direction", "tech_element_id", new_column_name="tech_domain_id")

    # 4. 重命名外键列 - core_talent_tech_tag
    op.alter_column("core_talent_tech_tag", "tech_element_id", new_column_name="tech_domain_id")

    # 5. 重命名外键列 - config_venue_tech_binding
    op.alter_column("config_venue_tech_binding", "tech_element_id", new_column_name="tech_domain_id")

    # 6. 重命名外键列 - rel_author_tech_belong
    op.alter_column("rel_author_tech_belong", "tech_element_id", new_column_name="tech_domain_id")

    # 7. 重命名外键列 - sync_collect_task
    op.alter_column("sync_collect_task", "tech_element_id", new_column_name="tech_domain_id")

    # 8. 重命名唯一约束 (config_venue_tech_binding)
    op.drop_constraint("uq_venue_tech_element", "config_venue_tech_binding", type_="unique")
    op.create_unique_constraint(
        "uq_venue_tech_domain",
        "config_venue_tech_binding",
        ["venue_id", "tech_domain_id"]
    )

    # 9. 删除旧的外键约束并创建新的
    # core_tech_direction
    op.drop_constraint("core_tech_direction_tech_element_id_fkey", "core_tech_direction", type_="foreignkey")
    op.create_foreign_key(
        "core_tech_direction_tech_domain_id_fkey",
        "core_tech_direction",
        "core_tech_domain",
        ["tech_domain_id"],
        ["tech_domain_id"]
    )

    # core_talent_tech_tag
    op.drop_constraint("core_talent_tech_tag_tech_element_id_fkey", "core_talent_tech_tag", type_="foreignkey")
    op.create_foreign_key(
        "core_talent_tech_tag_tech_domain_id_fkey",
        "core_talent_tech_tag",
        "core_tech_domain",
        ["tech_domain_id"],
        ["tech_domain_id"]
    )

    # config_venue_tech_binding (实际约束名: fk_venue_binding_tech)
    op.drop_constraint("fk_venue_binding_tech", "config_venue_tech_binding", type_="foreignkey")
    op.create_foreign_key(
        "fk_venue_binding_domain",
        "config_venue_tech_binding",
        "core_tech_domain",
        ["tech_domain_id"],
        ["tech_domain_id"]
    )

    # rel_author_tech_belong (实际约束名: fk_author_tech_tech)
    op.drop_constraint("fk_author_tech_tech", "rel_author_tech_belong", type_="foreignkey")
    op.create_foreign_key(
        "fk_author_tech_domain",
        "rel_author_tech_belong",
        "core_tech_domain",
        ["tech_domain_id"],
        ["tech_domain_id"]
    )

    # sync_collect_task (实际约束名: fk_collect_task_tech_element)
    op.drop_constraint("fk_collect_task_tech_element", "sync_collect_task", type_="foreignkey")
    op.create_foreign_key(
        "fk_collect_task_tech_domain",
        "sync_collect_task",
        "core_tech_domain",
        ["tech_domain_id"],
        ["tech_domain_id"]
    )

    # 10. 重命名索引
    # core_tech_direction (实际索引名: ix_tech_direction_element)
    op.drop_index("ix_tech_direction_element", "core_tech_direction")
    op.create_index("ix_tech_direction_domain", "core_tech_direction", ["tech_domain_id"])

    # core_talent_tech_tag (实际索引名: ix_talent_tech_tag_element, ix_talent_tech_enabled_element)
    op.drop_index("ix_talent_tech_tag_element", "core_talent_tech_tag")
    op.drop_index("ix_talent_tech_enabled_element", "core_talent_tech_tag")
    op.create_index("ix_talent_tech_tag_domain", "core_talent_tech_tag", ["tech_domain_id"])
    op.create_index(
        "ix_talent_tech_enabled_domain",
        "core_talent_tech_tag",
        ["tech_domain_id"],
        postgresql_where=sa.text("is_enabled = true")
    )

    # sync_collect_task
    op.drop_index("ix_sync_collect_task_tech_element_id", "sync_collect_task")
    op.create_index("ix_sync_collect_task_tech_domain_id", "sync_collect_task", ["tech_domain_id"])

    # rel_author_tech_belong: 删除旧索引，创建新索引
    op.drop_index("ix_author_tech_tech", "rel_author_tech_belong")
    op.create_index("ix_author_tech_domain", "rel_author_tech_belong", ["tech_domain_id"])

    # 11. 重命名统计表字段
    op.alter_column("stat_overview_snapshot", "tech_element_count", new_column_name="tech_domain_count")


def downgrade() -> None:
    """回滚：重命名技术领域为技术要素"""

    # 1. 重命名索引 (逆序)
    op.drop_index("ix_author_tech_domain", "rel_author_tech_belong")
    op.create_index("ix_author_tech_tech", "rel_author_tech_belong", ["tech_element_id"])

    op.drop_index("ix_sync_collect_task_tech_domain_id", "sync_collect_task")
    op.create_index("ix_sync_collect_task_tech_element_id", "sync_collect_task", ["tech_element_id"])

    op.drop_index("ix_talent_tech_enabled_domain", "core_talent_tech_tag")
    op.drop_index("ix_talent_tech_tag_domain", "core_talent_tech_tag")
    op.create_index("ix_talent_tech_enabled_element", "core_talent_tech_tag", ["tech_element_id"])
    op.create_index("ix_talent_tech_tag_element", "core_talent_tech_tag", ["tech_element_id"])

    op.drop_index("ix_tech_direction_domain", "core_tech_direction")
    op.create_index("ix_tech_direction_element", "core_tech_direction", ["tech_element_id"])

    # 2. 重命名外键约束
    op.drop_constraint("fk_collect_task_tech_domain", "sync_collect_task", type_="foreignkey")
    op.create_foreign_key(
        "fk_collect_task_tech_element",
        "sync_collect_task",
        "core_tech_element",
        ["tech_element_id"],
        ["tech_element_id"]
    )

    op.drop_constraint("fk_author_tech_domain", "rel_author_tech_belong", type_="foreignkey")
    op.create_foreign_key(
        "fk_author_tech_tech",
        "rel_author_tech_belong",
        "core_tech_element",
        ["tech_element_id"],
        ["tech_element_id"]
    )

    op.drop_constraint("fk_venue_binding_domain", "config_venue_tech_binding", type_="foreignkey")
    op.create_foreign_key(
        "fk_venue_binding_tech",
        "config_venue_tech_binding",
        "core_tech_element",
        ["tech_element_id"],
        ["tech_element_id"]
    )

    op.drop_constraint("core_talent_tech_tag_tech_domain_id_fkey", "core_talent_tech_tag", type_="foreignkey")
    op.create_foreign_key(
        "core_talent_tech_tag_tech_element_id_fkey",
        "core_talent_tech_tag",
        "core_tech_element",
        ["tech_element_id"],
        ["tech_element_id"]
    )

    op.drop_constraint("core_tech_direction_tech_domain_id_fkey", "core_tech_direction", type_="foreignkey")
    op.create_foreign_key(
        "core_tech_direction_tech_element_id_fkey",
        "core_tech_direction",
        "core_tech_element",
        ["tech_element_id"],
        ["tech_element_id"]
    )

    # 3. 重命名唯一约束
    op.drop_constraint("uq_venue_tech_domain", "config_venue_tech_binding", type_="unique")
    op.create_unique_constraint(
        "uq_venue_tech_element",
        "config_venue_tech_binding",
        ["venue_id", "tech_element_id"]
    )

    # 4. 重命名列 (逆序)
    op.alter_column("sync_collect_task", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("rel_author_tech_belong", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("config_venue_tech_binding", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("core_talent_tech_tag", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("core_tech_direction", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("core_tech_domain", "tech_domain_id", new_column_name="tech_element_id")
    op.alter_column("core_tech_domain", "domain_code", new_column_name="element_code")
    op.alter_column("core_tech_domain", "domain_name", new_column_name="element_name")
    op.alter_column("core_tech_domain", "domain_name_en", new_column_name="element_name_en")
    op.alter_column("core_tech_domain", "domain_desc", new_column_name="element_desc")
    op.alter_column("stat_overview_snapshot", "tech_domain_count", new_column_name="tech_element_count")

    # 5. 重命名主表
    op.rename_table("core_tech_domain", "core_tech_element")
