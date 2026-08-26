"""Open-API authentication dependency (X-API-Key + scope check)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.services.api_key_service import ApiKeyService


def require_api_key(scope: str):
    """Build a dependency verifying the X-API-Key header and requiring ``scope``.

    Returns a dependency yielding the principal dict:
    ``{"role": "api_agent", "api_key_id", "key_name", "scopes", "rate_limit_per_minute"}``
    """

    async def _dependency(
        api_key: str | None = Header(None, alias="X-API-Key"),
        session: AsyncSession = Depends(get_async_session),
    ) -> dict:
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
        service = ApiKeyService(session)
        record = await service.verify_key(api_key)
        if record is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key.")
        if not service.has_scope(record, scope):
            raise HTTPException(
                status_code=403,
                detail=f"API key lacks required scope: {scope}.",
            )
        await session.commit()  # persist the last_used_at touch
        return {
            "role": "api_agent",
            "api_key_id": record.api_key_id,
            "key_name": record.key_name,
            "scopes": record.scopes or [],
            "rate_limit_per_minute": record.rate_limit_per_minute,
        }

    return _dependency
