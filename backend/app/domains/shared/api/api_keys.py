"""API key management endpoints (super_admin)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth_deps import require_super_admin
from app.domains.shared.schemas.api_key import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListItem,
    ApiKeySetActiveRequest,
)
from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.audit_service import AuditService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def _to_item(r: Any) -> ApiKeyListItem:
    return ApiKeyListItem(
        api_key_id=r.api_key_id,
        key_name=r.key_name,
        key_prefix=r.key_prefix,
        scopes=r.scopes or [],
        is_active=r.is_active,
        rate_limit_per_minute=r.rate_limit_per_minute,
        expires_at=r.expires_at,
        last_used_at=r.last_used_at,
        created_at=r.created_at,
    )


@router.post("", response_model=ApiKeyCreatedResponse, summary="创建 API Key（super_admin）")
async def create_api_key(
    req: ApiKeyCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    admin: dict = Depends(require_super_admin),
) -> ApiKeyCreatedResponse:
    service = ApiKeyService(session)
    created = await service.create_key(
        key_name=req.key_name,
        scopes=req.scopes,
        created_by=admin["user_id"],
        rate_limit_per_minute=req.rate_limit_per_minute,
        expires_at=req.expires_at,
    )
    await session.commit()
    await AuditService.log_data_operation(
        user_id=admin["user_id"],
        operation="create",
        resource_type="api_key",
        resource_id=str(created["record"].api_key_id),
        status="success",
        detail={"key_name": req.key_name, "scopes": req.scopes},
    )
    r = created["record"]
    return ApiKeyCreatedResponse(
        api_key_id=r.api_key_id,
        key_name=r.key_name,
        key_prefix=r.key_prefix,
        scopes=r.scopes or [],
        is_active=r.is_active,
        expires_at=r.expires_at,
        plaintext_key=created["key"],
    )


@router.get("", response_model=list[ApiKeyListItem], summary="列出 API Key（super_admin）")
async def list_api_keys(
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> list[ApiKeyListItem]:
    records = await ApiKeyService(session).list_keys()
    return [_to_item(r) for r in records]


@router.patch(
    "/{api_key_id}", response_model=ApiKeyListItem, summary="吊销/启用 API Key（super_admin）"
)
async def set_api_key_active(
    api_key_id: int,
    req: ApiKeySetActiveRequest,
    session: AsyncSession = Depends(get_async_session),
    admin: dict = Depends(require_super_admin),
) -> ApiKeyListItem:
    service = ApiKeyService(session)
    record = await service.get_by_id(api_key_id)
    if not record:
        raise HTTPException(status_code=404, detail="API key not found")
    await service.set_active(api_key_id, req.is_active)
    await session.commit()
    await session.refresh(record)
    await AuditService.log_data_operation(
        user_id=admin["user_id"],
        operation="update",
        resource_type="api_key",
        resource_id=str(api_key_id),
        status="success",
        detail={"is_active": req.is_active},
    )
    return _to_item(record)
