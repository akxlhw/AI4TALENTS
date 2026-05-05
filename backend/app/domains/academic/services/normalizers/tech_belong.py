"""
Tech belong calculator for author-tech element relationships.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import AuthorTechBelong, RawWork
from app.domains.academic.models.venue import Venue


class TechBelongCalculator:
    """计算作者-技术领域归属关系"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_for_venue(
        self, venue_id: int, tech_domain_id: int, task_id: int | None = None
    ) -> int:
        """Calculate author-tech relationships for a venue

        Returns number of relationships created
        """
        # Get the Venue to find its openalex_source_id
        venue_result = await self.session.execute(select(Venue).where(Venue.venue_id == venue_id))
        venue = venue_result.scalar_one_or_none()
        if not venue or not venue.openalex_source_id:
            return 0

        # Batch preload existing AuthorTechBelong for this venue + tech_domain
        # to avoid N+1 queries inside the loop
        existing_result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.tech_domain_id == tech_domain_id,
                AuthorTechBelong.source_venue_id == venue_id,
            )
        )
        existing_belongs: dict[str, AuthorTechBelong] = {
            b.openalex_author_id: b for b in existing_result.scalars().all()
        }

        # Get all RawWorks from this venue using openalex_source_id
        result = await self.session.execute(
            select(RawWork).where(RawWork.source_id == venue.openalex_source_id)
        )
        works = result.scalars().all()

        # Group by author
        author_stats: dict[str, dict] = {}

        for work in works:
            if work.author_ids:
                try:
                    author_ids = json.loads(work.author_ids)
                    for author_id in author_ids:
                        if author_id not in author_stats:
                            author_stats[author_id] = {
                                "work_count": 0,
                                "first_year": work.publication_year,
                                "last_year": work.publication_year,
                            }
                        author_stats[author_id]["work_count"] += 1
                        if work.publication_year:
                            if author_stats[author_id]["first_year"]:
                                author_stats[author_id]["first_year"] = min(
                                    author_stats[author_id]["first_year"], work.publication_year
                                )
                            if author_stats[author_id]["last_year"]:
                                author_stats[author_id]["last_year"] = max(
                                    author_stats[author_id]["last_year"], work.publication_year
                                )
                except (KeyError, TypeError):
                    pass

        # Create or update relationships using preloaded map (no N+1)
        count = 0
        for author_id, stats in author_stats.items():
            belong = existing_belongs.get(author_id)

            if belong:
                # Update existing record
                belong.work_count_in_venue = stats["work_count"]
                belong.first_work_year = stats["first_year"]
                belong.last_work_year = stats["last_year"]
                belong.source_venue_id = venue_id
                belong.source_task_id = task_id
            else:
                # Create new record
                belong = AuthorTechBelong(
                    openalex_author_id=author_id,
                    tech_domain_id=tech_domain_id,
                    source_venue_id=venue_id,
                    work_count_in_venue=stats["work_count"],
                    first_work_year=stats["first_year"],
                    last_work_year=stats["last_year"],
                    source_task_id=task_id,
                )
                self.session.add(belong)
            count += 1

        await self.session.flush()
        return count
