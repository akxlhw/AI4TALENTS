"""AuthorTechBelongRepository — split from raw_data_repository.py (P2-3)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import AuthorTechBelong

logger = logging.getLogger(__name__)


class AuthorTechBelongRepository:
    """Author-TechDomain relationship repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, belong: AuthorTechBelong) -> AuthorTechBelong:
        """Create an author-tech belong relationship"""
        self.session.add(belong)
        await self.session.flush()
        await self.session.refresh(belong)
        return belong

    async def upsert(self, belong: AuthorTechBelong) -> AuthorTechBelong:
        """Create or update an author-tech belong relationship"""
        existing = await self.get_by_author_tech_venue(
            belong.openalex_author_id,
            belong.tech_domain_id,
            belong.source_venue_id,
        )
        if existing:
            existing.work_count_in_venue = belong.work_count_in_venue
            existing.first_work_year = belong.first_work_year
            existing.last_work_year = belong.last_work_year
            existing.source_task_id = belong.source_task_id
            await self.session.flush()
            return existing
        else:
            return await self.create(belong)

    async def get_by_author_tech_venue(
        self, openalex_author_id: str, tech_domain_id: int, source_venue_id: int | None
    ) -> AuthorTechBelong | None:
        """Get relationship by author, tech domain and venue"""
        result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.openalex_author_id == openalex_author_id,
                AuthorTechBelong.tech_domain_id == tech_domain_id,
                AuthorTechBelong.source_venue_id == source_venue_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tech_domain(self, tech_domain_id: int) -> list[AuthorTechBelong]:
        """Get all relationships for a tech domain"""
        result = await self.session.execute(
            select(AuthorTechBelong).where(AuthorTechBelong.tech_domain_id == tech_domain_id)
        )
        return list(result.scalars().all())
