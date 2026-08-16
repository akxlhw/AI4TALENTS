"""
User administration endpoints (list/create/update/approve).

Split from permissions.py; routes keep the original /users prefix.
端点实现进一步拆分为 user_admin_list.py（列表/待审核/创建）与
user_admin_detail.py（详情/更新/活动/启停/审批），本文件聚合为原路由；
include 顺序保持原路由注册顺序不变（/pending 先于 /{user_id}）。
"""

from fastapi import APIRouter

from app.domains.shared.api import user_admin_detail, user_admin_list

router = APIRouter()
router.include_router(user_admin_list.router)
router.include_router(user_admin_detail.router)

__all__ = ["router"]
