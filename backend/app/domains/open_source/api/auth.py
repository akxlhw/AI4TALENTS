"""
Shared auth helpers for Open Source API endpoints.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.auth import verify_access_token
from app.domains.shared.models.enums import UserRoleType


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Extract current user from Bearer token in Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def require_admin(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    user = await get_current_user(authorization)
    if user.get("role") not in (UserRoleType.ADMIN.value, UserRoleType.SUPER_ADMIN.value):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_super_admin(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    user = await get_current_user(authorization)
    if user.get("role") != UserRoleType.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user
