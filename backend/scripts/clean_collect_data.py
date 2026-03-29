"""
清理现有采集数据脚本
删除所有采集相关的数据，保留系统配置
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def clean_collect_data():
    """清理采集相关数据"""

    async with AsyncSessionLocal() as session:
        print("=" * 60)
        print("Starting to clean collect data...")
        print("=" * 60)

        # 要清理的表（按外键依赖顺序）
        tables_to_clean = [
            # 原始数据层（如果存在）
            ("raw_work", "Raw Work"),
            ("raw_author", "Raw Author"),
            ("raw_institution", "Raw Institution"),
            ("rel_author_tech_belong", "Author Tech Belong"),

            # 标准化层（如果存在）
            ("std_author", "Std Author"),
            ("std_school_alias", "Std School Alias"),
            ("std_school", "Std School"),

            # OpenAlex 表（如果存在）
            ("openalex_work_author", "OpenAlex Work Author"),
            ("openalex_work_concept", "OpenAlex Work Concept"),
            ("openalex_work", "OpenAlex Work"),
            ("openalex_author", "OpenAlex Author"),
            ("openalex_institution", "OpenAlex Institution"),
            ("openalex_source", "OpenAlex Source"),
            ("openalex_concept", "OpenAlex Concept"),
            ("openalex_publisher", "OpenAlex Publisher"),
            ("openalex_funder", "OpenAlex Funder"),

            # 采集任务相关
            ("sync_venue_sub_task", "Venue Sub Task"),
            ("sync_collect_task", "Collect Task"),

            # Venue配置（可选择保留）
            ("config_venue_tech_binding", "Venue Tech Binding"),
            ("config_venue", "Venue Config"),

            # 核心业务数据
            ("core_selected_work", "Selected Work"),
            ("core_talent_tech_tag", "Talent Tech Tag"),
            ("core_collaboration", "Collaboration"),
            ("core_work_author", "Work Author"),
            ("core_role_profile", "Role Profile"),
            ("core_talent", "Talent"),

            # 学校相关（可选清理）
            ("core_school_alias", "School Alias"),
            ("core_school", "School"),

            # 统计快照
            ("stat_school_snapshot", "School Stat Snapshot"),
            ("stat_overview_snapshot", "Overview Stat Snapshot"),

            # 收藏相关
            ("iam_talent_pool_member", "Talent Pool Member"),
            ("iam_talent_note", "Talent Note"),
            ("iam_follow_record", "Follow Record"),
            ("iam_talent_pool", "Talent Pool"),
            ("iam_favorite_talent", "Favorite Talent"),
        ]

        total_deleted = 0

        for table_name, description in tables_to_clean:
            try:
                # 检查表是否存在
                check_sql = text(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                result = await session.execute(check_sql)
                if not result.fetchone():
                    print(f"  [SKIP] {description} ({table_name}): table not exists")
                    continue

                # 获取记录数
                count_sql = text(f"SELECT COUNT(*) FROM {table_name}")
                count_result = await session.execute(count_sql)
                count = count_result.scalar()

                if count == 0:
                    print(f"  [EMPTY] {description} ({table_name}): already empty")
                    continue

                # 删除数据
                delete_sql = text(f"DELETE FROM {table_name}")
                await session.execute(delete_sql)
                await session.commit()

                print(f"  [DELETED] {description} ({table_name}): {count:,} records")
                total_deleted += count

            except Exception as e:
                print(f"  [ERROR] {description} ({table_name}): {e}")
                await session.rollback()

        print("=" * 60)
        print(f"Clean completed! Total deleted: {total_deleted:,} records")
        print("=" * 60)

        # 重置自增ID（SQLite）
        print("\nResetting auto-increment IDs...")
        for table_name, _ in tables_to_clean:
            try:
                # 检查表是否存在
                check_sql = text(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                result = await session.execute(check_sql)
                if result.fetchone():
                    reset_sql = text(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                    await session.execute(reset_sql)
            except:
                pass

        await session.commit()
        print("Auto-increment IDs reset done")

        # 保留的系统配置数据
        print("\nPreserved system data:")
        print("  - User accounts (iam_user_account)")
        print("  - User permissions (iam_user_permission)")
        print("  - User school scope (iam_user_school_scope)")
        print("  - Countries (core_country)")
        print("  - Tech elements (core_tech_element)")
        print("  - Tech directions (core_tech_direction)")
        print("  - Audit logs (audit_operation_log)")


if __name__ == "__main__":
    asyncio.run(clean_collect_data())
