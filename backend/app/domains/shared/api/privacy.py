"""Privacy compliance API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_user
from app.domains.shared.schemas.common import SuccessResponse
from app.domains.shared.schemas.privacy import PrivacyConsentRequest, PrivacyConsentResponse
from app.domains.shared.services.privacy_service import PrivacyService
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.get(
    "/policy",
    summary="获取隐私政策",
    description="返回当前版本的隐私政策全文（Markdown 格式）",
)
async def get_privacy_policy():
    """Return privacy policy text."""
    return {"content": PrivacyService.get_privacy_policy_text()}


@router.get(
    "/terms",
    summary="获取用户协议",
    description="返回当前版本的用户协议全文（Markdown 格式）",
)
async def get_terms_of_use():
    """Return terms of use text."""
    return {"content": PrivacyService.get_terms_of_use_text()}


@router.get(
    "/consent-status",
    response_model=PrivacyConsentResponse,
    summary="获取当前用户同意状态",
    description="返回当前登录用户的隐私政策/用户协议同意状态",
)
async def get_consent_status(
    current_user: dict = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get current user's consent status."""
    user_service = UserService(session)
    privacy_service = PrivacyService(user_service)
    status = await privacy_service.get_privacy_consent_status(current_user["user_id"])

    if not status:
        return PrivacyConsentResponse()

    return PrivacyConsentResponse(
        privacy_policy_accepted_at=status.get("privacy_policy_accepted_at"),
        privacy_policy_version=status.get("privacy_policy_version"),
        terms_of_use_accepted_at=status.get("terms_of_use_accepted_at"),
        terms_of_use_version=status.get("terms_of_use_version"),
        storage_consent_level=status.get("storage_consent_level", "necessary"),
    )


@router.post(
    "/consent",
    response_model=SuccessResponse,
    summary="更新同意记录",
    description="提交或更新用户的隐私政策/用户协议同意记录",
)
async def update_consent(
    data: PrivacyConsentRequest,
    current_user: dict = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update user's consent record."""
    user_service = UserService(session)
    privacy_service = PrivacyService(user_service)

    success = await privacy_service.update_privacy_consent(
        user_id=current_user["user_id"],
        policy_version=data.policy_version,
        terms_version=data.terms_version,
        storage_consent_level=data.storage_consent_level,
        accepted=data.accepted,
    )

    if not success:
        return SuccessResponse(success=False, message="用户不存在或更新失败")

    return SuccessResponse(message="同意记录已更新")
