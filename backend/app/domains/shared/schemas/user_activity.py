"""
Schemas for user activity timeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ActivityItem(BaseModel):
    """Standardized activity event for user timeline display."""

    activity_id: int
    activity_time: datetime
    activity_type: Literal[
        "login",
        "login_failure",
        "profile_update",
        "role_change",
        "account_activated",
        "account_deactivated",
        "account_created",
        "account_approved",
        "account_rejected",
        "scope_grant",
        "scope_revoke",
        "password_change",
        "other",
    ]
    actor: dict | None = None
    target_user_id: int
    description: str
    detail: dict | None = None
    ip: str | None = None
    status: str


class UserActivityListResponse(BaseModel):
    """Paginated user activity response."""

    items: list[ActivityItem]
    total: int
    page: int
    page_size: int
