"""
Talents API endpoints.
Provides talent list, detail, and filtering.

端点实现已按分组拆分为子路由模块（talent_queries / talent_export /
talent_collaborations），本文件聚合为原路由；include 顺序保持原路由
注册顺序不变。

Architecture: Endpoint -> Service -> Repository
"""

from fastapi import APIRouter

from app.domains.academic.api import (
    talent_collaborations,
    talent_export,
    talent_queries,
)

router = APIRouter()
router.include_router(talent_queries.router)
router.include_router(talent_export.router)
router.include_router(talent_collaborations.router)

__all__ = ["router"]
