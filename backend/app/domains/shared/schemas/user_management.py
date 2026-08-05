"""
User and permission management schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    """User response."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None
    is_active: bool
    status: str
    employee_id: str | None = None
    default_view: str = "tech_domain"
    last_login_at: datetime | None = None
    privacy_policy_accepted_at: datetime | None = None
    privacy_policy_version: str | None = None
    terms_of_use_accepted_at: datetime | None = None
    terms_of_use_version: str | None = None
    storage_consent_level: str = "necessary"


class UserListResponse(BaseModel):
    """User list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserCreateRequest(BaseModel):
    """Create user request."""

    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="user")
    display_name: str | None = None
    employee_id: str | None = Field(default=None, pattern=r"^[a-zA-Z]\d{8}$")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.core.auth import validate_password_strength

        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserUpdateRequest(BaseModel):
    """Update user request."""

    display_name: str | None = None
    department: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ScopeResponse(BaseModel):
    """User scope response."""

    scope_id: int
    user_id: int
    scope_type: str
    scope_value: str
    granted_by: int
    granted_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    notes: str | None = None


class ScopeCreateRequest(BaseModel):
    """Create scope request."""

    user_id: int
    scope_type: str = Field(..., pattern="^(school|country|tech_domain|all)$")
    scope_value: str
    expires_at: datetime | None = None
    notes: str | None = None


class DefaultViewRequest(BaseModel):
    """Update default view request."""

    default_view: str = Field(..., pattern="^(tech_domain|country_school)$")


class SchoolAccessResponse(BaseModel):
    """School access check response."""

    school_id: int
    has_access: bool


class DefaultViewResponse(BaseModel):
    """Default view response."""

    default_view: str


class ScopeListResponse(BaseModel):
    """Scope list response."""

    items: list[ScopeResponse]
    total: int
