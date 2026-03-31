"""
采集任务测试脚本
测试采集任务的创建和执行
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.sync import CollectTask
from app.models.tech_element import TechElement
from app.models.venue import VenueTechBinding, VenueSubTask
from datetime import datetime
import uuid


async def test_collect_task():
    """测试采集任务执行"""
    print("=" * 60)
    print("采集任务测试")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # 1. 检查技术要素
        print("\n1. 检查技术要素...")
        result = await session.execute(select(TechElement).limit(1))
        tech = result.scalar_one_or_none()
        if not tech:
            print("错误: 没有找到技术要素")
            return
        print(f"   技术要素: {tech.element_name} (ID: {tech.tech_element_id})")

        # 2. 检查绑定的 venue
        print("\n2. 检查绑定的顶会顶刊...")
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(VenueTechBinding)
            .options(selectinload(VenueTechBinding.venue))
            .where(VenueTechBinding.tech_element_id == tech.tech_element_id)
            .where(VenueTechBinding.is_enabled == True)
        )
        bindings = list(result.scalars().all())
        print(f"   已启用绑定数: {len(bindings)}")
        for b in bindings:
            print(f"   - {b.venue.venue_name}")

        if not bindings:
            print("   警告: 没有启用的绑定，无法执行采集")
            return

        # 3. 取消之前的待执行任务
        print("\n3. 取消之前的待执行任务...")
        from sqlalchemy import update
        await session.execute(
            update(CollectTask)
            .where(CollectTask.status.in_(["pending", "running"]))
            .values(status="cancelled", current_step="测试取消")
        )
        await session.commit()
        print("   已取消")

        # 4. 创建新任务
        print("\n4. 创建新任务...")
        task = CollectTask(
            task_code=f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
            tech_element_id=tech.tech_element_id,
            collect_mode="full",
            triggered_by=1,
            triggered_at=datetime.utcnow(),
            status="pending",
            current_step="测试任务"
        )
        session.add(task)
        await session.flush()
        task_id = task.task_id

        # 创建 VenueSubTask
        from datetime import timedelta
        time_start = datetime(2020, 1, 1)
        time_end = datetime.utcnow()

        for binding in bindings:
            sub_task = VenueSubTask(
                task_id=task_id,
                venue_id=binding.venue_id,
                status="pending",
                time_window_start=time_start,
                time_window_end=time_end,
            )
            session.add(sub_task)

        await session.commit()
        print(f"   创建任务 ID: {task_id}")

    # 5. 执行任务（使用新的 session）
    print("\n5. 执行采集任务...")
    print("-" * 60)

    try:
        from app.services.unified_collect_service import UnifiedCollectService

        async with AsyncSessionLocal() as session:
            service = UnifiedCollectService(session)
            progress = await service.execute_task(task_id)

            print("-" * 60)
            print(f"\n任务执行结果:")
            print(f"   状态: {progress.status}")
            print(f"   Works: {progress.total_works}")
            print(f"   Authors: {progress.total_authors}")
            print(f"   Normalized: {progress.normalized_authors}")
            print(f"   Synced: {progress.synced_authors}")
            if progress.errors:
                print(f"   错误: {progress.errors}")

    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()

        # 更新任务状态
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(CollectTask)
                .where(CollectTask.task_id == task_id)
                .values(status="failed", error_message=str(e), current_step="执行失败")
            )
            await session.commit()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_collect_task())
