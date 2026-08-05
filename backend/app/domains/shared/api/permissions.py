"""
User and permission management API endpoints.

Endpoint implementations live in `user_admin.py` / `user_scopes.py` /
`user_access.py` (split from the original monolith); schemas live in
`app.domains.shared.schemas.user_management`. The aggregated `router`
keeps the original routes unchanged.
"""

from fastapi import APIRouter

from app.domains.shared.api import user_access, user_admin, user_scopes
from app.domains.shared.schemas.user_management import (
    DefaultViewRequest,
    DefaultViewResponse,
    SchoolAccessResponse,
    ScopeCreateRequest,
    ScopeListResponse,
    ScopeResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter()
router.include_router(user_admin.router)
router.include_router(user_scopes.router)
router.include_router(user_access.router)

__all__ = [
    "router",
    "UserResponse",
    "UserListResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "ScopeResponse",
    "ScopeCreateRequest",
    "DefaultViewRequest",
    "SchoolAccessResponse",
    "DefaultViewResponse",
    "ScopeListResponse",
]
