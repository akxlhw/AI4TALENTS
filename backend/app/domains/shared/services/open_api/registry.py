"""Cross-domain search registry (inversion: domains register, shared consumes).

The cross-domain isolation rule forbids shared from importing business-domain
internals. Each domain registers a provider FACTORY here (importing shared is
allowed for domains); the search router in shared only consumes the registry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class UnifiedTalentSummary(BaseModel):
    """Domain-agnostic talent summary for /open-api/search aggregation."""

    domain: str
    talent_id: int
    name: str
    identifier: str | None = None  # github_login / handle
    url: str | None = None  # public profile page; PII links stay per-domain policy
    tags: list[str] = Field(default_factory=list)


class SearchProvider(Protocol):
    domain: str

    def search(self, keyword: str, limit: int) -> Awaitable[list[UnifiedTalentSummary]]: ...


# Provider factory: bound to a request-scoped DB session when invoked.
ProviderFactory = Callable[[AsyncSession], SearchProvider]

_REGISTRY: dict[str, ProviderFactory] = {}


def register_search_provider(domain: str, factory: ProviderFactory) -> None:
    """Register (or replace) the provider factory for a domain."""
    _REGISTRY[domain] = factory


def get_search_provider_factories(
    domains: list[str] | None = None,
) -> dict[str, ProviderFactory]:
    if not domains:
        return dict(_REGISTRY)
    return {d: _REGISTRY[d] for d in domains if d in _REGISTRY}


def registered_domains() -> list[str]:
    return sorted(_REGISTRY)


async def run_provider_isolated(
    factory: ProviderFactory,
    keyword: str,
    limit: int,
    timeout_seconds: float = 5.0,
) -> list[UnifiedTalentSummary]:
    """Run one provider on a dedicated session.

    AsyncSession forbids concurrent operations, so parallel domains must not
    share a session; the API layer cannot open sessions itself (layering
    rule), hence this service-side helper.
    """
    import asyncio

    from app.core.database import AsyncSessionLocal

    session = AsyncSessionLocal()
    try:
        provider = factory(session)
        result = await asyncio.wait_for(provider.search(keyword, limit), timeout=timeout_seconds)
        return list(result)
    finally:
        await session.close()
