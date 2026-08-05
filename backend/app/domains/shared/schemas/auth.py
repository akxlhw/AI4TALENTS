"""
Authentication schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 8 * 3600  # 8 hours in seconds
    user: UserInfo


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserInfo(BaseModel):
    """User information."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    employee_id: str = Field(..., pattern=r"^[a-zA-Z]\d{8}$")
    display_name: str | None = Field(default=None, max_length=100)
    privacy_policy_accepted: bool = Field(default=False)
    terms_of_use_accepted: bool = Field(default=False)
    storage_consent_level: str = Field(default="necessary")


class CurrentUser(BaseModel):
    """Current user response."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    privacy_policy_accepted_at: datetime | None = None
    privacy_policy_version: str | None = None
    terms_of_use_accepted_at: datetime | None = None
    terms_of_use_version: str | None = None
    storage_consent_level: str = "necessary"
