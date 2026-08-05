"""
Self-service access query endpoints (my schools/domains/countries/default view).

Split from permissions.py; routes keep the original /users prefix.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_user
from app.domains.shared.schemas.user_management import (
    DefaultViewRequest,
    DefaultViewResponse,
    SchoolAccessResponse,
)
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/me/scopes/schools",
    response_model=list[int],
    summary="获取当前用户可访问的学校",
    description="返回当前用户有权访问的学校ID列表",
)
async def get_my_accessible_schools(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible school IDs."""
    service = UserService(session)
    school_ids = await service.get_accessible_school_ids(current_user["user_id"])
    return school_ids


@router.get(
    "/me/scopes/check/{school_id}",
    response_model=SchoolAccessResponse,
    summary="检查学校访问权限",
    description="检查当前用户是否有权访问指定学校",
)
async def check_school_access(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Check if current user can access a specific school."""
    service = UserService(session)
    has_access = await service.check_user_has_access(
        current_user["user_id"],
        school_id,
    )

    return SchoolAccessResponse(
        school_id=school_id,
        has_access=has_access,
    )


@router.get(
    "/me/scopes/tech-domains",
    response_model=list[int],
    summary="获取当前用户可访问的技术领域",
    description="返回当前用户有权访问的技术领域ID列表",
)
async def get_my_accessible_tech_domains(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible tech domain IDs."""
    service = UserService(session)
    tech_domain_ids = await service.get_accessible_tech_domain_ids(current_user["user_id"])
    return tech_domain_ids


@router.get(
    "/me/scopes/countries",
    response_model=list[str],
    summary="获取当前用户可访问的国家",
    description="返回当前用户有权访问的国家代码列表",
)
async def get_my_accessible_countries(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible country codes."""
    service = UserService(session)
    country_codes = await service.get_accessible_country_codes(current_user["user_id"])
    return country_codes


@router.get(
    "/me/default-view",
    response_model=DefaultViewResponse,
    summary="获取当前用户默认视角",
    description="返回用户的默认视角配置",
)
async def get_my_default_view(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's default view preference."""
    service = UserService(session)
    default_view = await service.get_user_default_view(current_user["user_id"])
    return DefaultViewResponse(default_view=default_view)


@router.put(
    "/me/default-view",
    response_model=DefaultViewResponse,
    summary="更新当前用户默认视角",
    description="更新用户的默认视角配置",
)
async def update_my_default_view(
    data: DefaultViewRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Update current user's default view preference."""
    service = UserService(session)
    success = await service.update_default_view_and_commit(
        current_user["user_id"],
        data.default_view,
    )

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return DefaultViewResponse(default_view=data.default_view)
