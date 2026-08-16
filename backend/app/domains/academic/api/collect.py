"""
Collect configuration API endpoints
采集配置相关接口

功能说明：
- 技术领域配置：管理技术领域关联的顶会顶刊
- 采集任务：基于技术领域触发采集，可配置年份范围
- 固定参数：数据类型（学者+论文+机构）
- 可配置参数：时间范围（起始年份~截止年份/至今）

端点实现已按分组拆分为子路由模块（collect_config / collect_tasks /
collect_task_actions / collect_options / collect_subtasks），本文件聚合为原
路由；include 顺序保持原路由注册顺序不变。
"""

from fastapi import APIRouter

from app.domains.academic.api import (
    collect_config,
    collect_options,
    collect_subtasks,
    collect_task_actions,
    collect_tasks,
)

router = APIRouter()
router.include_router(collect_config.router)
router.include_router(collect_tasks.router)
router.include_router(collect_task_actions.router)
router.include_router(collect_options.router)
router.include_router(collect_subtasks.router)

__all__ = ["router"]
