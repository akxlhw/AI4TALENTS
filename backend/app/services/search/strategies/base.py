"""Base class and shared context for search strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.talent_repository import TalentRepository
from app.services.search.types import SearchConfig


@dataclass
class SearchContext:
    """Shared context passed to search strategies."""

    session: AsyncSession
    talent_repo: TalentRepository
    embedding_service: Any
    config: SearchConfig
    strategies: dict[str, "SearchStrategy"] = field(default_factory=dict)


class SearchStrategy(ABC):
    """Abstract base class for search strategies."""

    def __init__(self, context: SearchContext) -> None:
        self.context = context

    @abstractmethod
    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
        fields: list[str] | None = None,
        fuzzy: bool = False,
        session: AsyncSession | None = None,
    ) -> dict:
        """Execute search.

        Args:
            query: Search query string.
            page: Page number (1-indexed).
            page_size: Results per page.
            filters: Optional filter dict.
            fields: Field list (keyword search only).
            fuzzy: Fuzzy matching flag (keyword search only).
            session: Optional session override (used by hybrid search for
                parallel execution with independent sessions).

        Returns:
            dict with ``total``, ``items``, and optional count fields.
        """
