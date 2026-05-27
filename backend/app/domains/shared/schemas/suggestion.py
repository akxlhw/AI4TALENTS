"""
Suggestion schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SuggestionCreate(BaseModel):
    """Schema for creating a suggestion."""

    category: str = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class SuggestionReply(BaseModel):
    """Schema for admin reply."""

    admin_reply: str | None = Field(default=None)
    status: str = Field(default="in_progress")


class SuggestionResponse(BaseModel):
    """Schema for suggestion response."""

    suggestion_id: int
    user_id: int
    username: str | None = None
    category: str
    subject: str
    content: str
    status: str
    admin_reply: str | None = None
    attachments: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
