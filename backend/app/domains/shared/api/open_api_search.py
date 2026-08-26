"""Cross-domain unified talent search (Open API).

Providers are registered by each domain into the shared registry (factory
inversion — shared never imports domain internals). Requests select domains
via the ``domains`` query param; every selected domain requires the
``<domain>:read`` scope.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.open_api_auth import require_valid_api_key
from app.domains.shared.services.open_api.registry import (
    get_search_provider_factories,
    registered_domains,
)

router = APIRouter(prefix="/open-api/search", tags=["Open API — Search"])

_require = require_valid_api_key()

_PER_DOMAIN_CAP = 20
_TIMEOUT_SECONDS = 5.0


@router.get("/talents", summary="跨域统一人才搜索（每域需 <域>:read scope）")
async def unified_search(
    keyword: str = Query(..., min_length=1, max_length=200),
    domains: str | None = Query(
        None, description="逗号分隔，如 academic,open_source；缺省=全部已注册域"
    ),
    per_domain: int = Query(5, ge=1, le=_PER_DOMAIN_CAP),
    session: AsyncSession = Depends(get_async_session),
    principal: dict = Depends(_require),
) -> dict:
    wanted = [d.strip() for d in domains.split(",") if d.strip()] if domains else None
    factories = get_search_provider_factories(wanted)
    unknown = [d for d in (wanted or []) if d not in registered_domains()]

    missing = [d for d in factories if f"{d}:read" not in principal["scopes"]]
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"API key lacks read scope for: {', '.join(f'{d}:read' for d in sorted(missing))}.",
        )

    providers = [(d, factory(session)) for d, factory in factories.items()]

    async def _run(provider) -> list:
        return await asyncio.wait_for(provider.search(keyword, per_domain), timeout=_TIMEOUT_SECONDS)

    results = await asyncio.gather(*[_run(p) for _, p in providers], return_exceptions=True)

    items: list[dict] = []
    errors: dict[str, str] = {}
    for (domain, _provider), result in zip(providers, results):
        if isinstance(result, Exception):
            errors[domain] = str(result)[:200]
        else:
            items.extend(s.model_dump(mode="json") for s in result)

    return {
        "keyword": keyword,
        "domains": [d for d, _ in providers],
        "unknown_domains": unknown,
        "items": items,
        "errors": errors,
    }
