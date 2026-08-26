"""API key management schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100, description="备注名")
    scopes: list[str] = Field(..., min_length=1, description="如 ['academic:read']")
    rate_limit_per_minute: int | None = Field(None, ge=1, le=10000)
    expires_at: datetime | None = None


class ApiKeyCreatedResponse(BaseModel):
    api_key_id: int
    key_name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    plaintext_key: str = Field(..., description="明文 Key，仅此一次返回")


class ApiKeyListItem(BaseModel):
    api_key_id: int
    key_name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    rate_limit_per_minute: int | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime | None


class ApiKeySetActiveRequest(BaseModel):
    is_active: bool
