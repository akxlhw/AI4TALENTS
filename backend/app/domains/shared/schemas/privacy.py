"""Privacy compliance schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PrivacyConsentRequest(BaseModel):
    """Request to update privacy consent."""

    policy_version: str
    terms_version: str
    storage_consent_level: str = "necessary"
    accepted: bool = True


class PrivacyConsentResponse(BaseModel):
    """Current privacy consent status."""

    privacy_policy_accepted_at: datetime | None = None
    privacy_policy_version: str | None = None
    terms_of_use_accepted_at: datetime | None = None
    terms_of_use_version: str | None = None
    storage_consent_level: str = "necessary"
