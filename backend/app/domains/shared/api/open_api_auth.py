"""Open-API authentication dependency (X-API-Key + scope check)."""

from __future__ import annotations

from typing import Any, cast

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.metrics import metrics
from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.open_api.rate_limiter import api_key_rate_limiter


def _check_per_key_rate_limit(api_key_id: int, rate_limit_per_minute: int | None) -> int:
    """Enforce the per-key rate limit when configured. Returns retry-after seconds."""
    if not rate_limit_per_minute:
        return 0
    return api_key_rate_limiter.check(api_key_id, rate_limit_per_minute)


def require_api_key(scope: str) -> Any:
    """Build a dependency verifying the X-API-Key header and requiring ``scope``.

    Returns a dependency yielding the principal dict:
    ``{"role": "api_agent", "api_key_id", "key_name", "scopes", "rate_limit_per_minute"}``
    """

    async def _dependency(
        request: Request,
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
        retry_after = _check_per_key_rate_limit(
            cast(int, record.api_key_id),
            cast("int | None", record.rate_limit_per_minute),
        )
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for this API key.",
                headers={"Retry-After": str(retry_after)},
            )
        await session.commit()  # persist the last_used_at touch
        metrics.counter(
            "open_api_requests_total",
            labels={"key_prefix": cast(str, record.key_prefix), "path": request.url.path},
        ).inc()
        return {
            "role": "api_agent",
            "api_key_id": record.api_key_id,
            "key_name": cast(str, record.key_name),
            "scopes": record.scopes or [],
            "rate_limit_per_minute": record.rate_limit_per_minute,
        }

    return _dependency


def require_valid_api_key() -> Any:
    """Key validity only; scope enforcement is the endpoint's job.

    For endpoints whose required scopes depend on request parameters (e.g. the
    cross-domain search endpoint validates `<domain>:read` per requested
    domain).
    """

    async def _dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
        session: AsyncSession = Depends(get_async_session),
    ) -> dict:
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
        record = await ApiKeyService(session).verify_key(api_key)
        if record is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key.")
        retry_after = _check_per_key_rate_limit(
            cast(int, record.api_key_id),
            cast("int | None", record.rate_limit_per_minute),
        )
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for this API key.",
                headers={"Retry-After": str(retry_after)},
            )
        await session.commit()  # persist the last_used_at touch
        metrics.counter(
            "open_api_requests_total",
            labels={"key_prefix": cast(str, record.key_prefix), "path": request.url.path},
        ).inc()
        return {
            "role": "api_agent",
            "api_key_id": record.api_key_id,
            "key_name": cast(str, record.key_name),
            "scopes": record.scopes or [],
            "rate_limit_per_minute": record.rate_limit_per_minute,
        }

    return _dependency
