"""
Authentication dependencies (current user resolution and role guards).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_access_token
from app.core.database import get_async_session
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.services.user_service import UserService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> dict | None:
    """
    Get current user from JWT token.
    Returns None if no valid token provided.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        return None

    user_id = int(payload.get("sub", 0))

    # Verify user exists and is active
    service = UserService(session)
    user = await service.get_by_id(user_id)

    if not user or not user.is_active:
        return None

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role_type,
        "display_name": user.display_name,
    }


async def require_user(
    current_user: dict | None = Depends(get_current_user),
) -> dict:
    """
    Require a valid authenticated user.
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(
    current_user: dict = Depends(require_user),
) -> dict:
    """
    Require admin or super_admin role.
    Raises 403 if not authorized.
    """
    if current_user["role"] not in [UserRoleType.ADMIN.value, UserRoleType.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


async def require_super_admin(
    current_user: dict = Depends(require_user),
) -> dict:
    """
    Require super_admin role.
    Raises 403 if not authorized.
    """
    if current_user["role"] != UserRoleType.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required",
        )
    return current_user
