"""
Tech belong calculator for author-tech element relationships.
"""
import json
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import RawWork, AuthorTechBelong
from app.models.venue import Venue


class TechBelongCalculator:
    """计算作者-技术要素归属关系"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_for_venue(
        self,
        venue_id: int,
        tech_element_id: int,
        task_id: Optional[int] = None
    ) -> int:
        """Calculate author-tech relationships for a venue

        Returns number of relationships created
        """
        # Get the Venue to find its openalex_source_id
        venue_result = await self.session.execute(
            select(Venue).where(Venue.venue_id == venue_id)
        )
        venue = venue_result.scalar_one_or_none()
        if not venue or not venue.openalex_source_id:
            return 0

        # Get all RawWorks from this venue using openalex_source_id
        result = await self.session.execute(
            select(RawWork).where(RawWork.source_id == venue.openalex_source_id)
        )
        works = result.scalars().all()

        # Group by author
        author_stats: Dict[str, Dict] = {}

        for work in works:
            if work.author_ids:
                try:
                    author_ids = json.loads(work.author_ids)
                    for author_id in author_ids:
                        if author_id not in author_stats:
                            author_stats[author_id] = {
                                "work_count": 0,
                                "first_year": work.publication_year,
                                "last_year": work.publication_year
                            }
                        author_stats[author_id]["work_count"] += 1
                        if work.publication_year:
                            if author_stats[author_id]["first_year"]:
                                author_stats[author_id]["first_year"] = min(
                                    author_stats[author_id]["first_year"],
                                    work.publication_year
                                )
                            if author_stats[author_id]["last_year"]:
                                author_stats[author_id]["last_year"] = max(
                                    author_stats[author_id]["last_year"],
                                    work.publication_year
                                )
                except:
                    pass

        # Create or update relationships (upsert to handle duplicates)
        count = 0
        for author_id, stats in author_stats.items():
            # Check if relationship already exists
            existing = await self.session.execute(
                select(AuthorTechBelong).where(
                    AuthorTechBelong.openalex_author_id == author_id,
                    AuthorTechBelong.tech_element_id == tech_element_id
                )
            )
            belong = existing.scalar_one_or_none()

            if belong:
                # Update existing record (but preserve original source_task_id)
                belong.work_count_in_venue = stats["work_count"]
                belong.first_work_year = stats["first_year"]
                belong.last_work_year = stats["last_year"]
                belong.source_venue_id = venue_id
                # NOTE: Do NOT update source_task_id - keep the original collection task ID
            else:
                # Create new record
                belong = AuthorTechBelong(
                    openalex_author_id=author_id,
                    tech_element_id=tech_element_id,
                    source_venue_id=venue_id,
                    work_count_in_venue=stats["work_count"],
                    first_work_year=stats["first_year"],
                    last_work_year=stats["last_year"],
                    source_task_id=task_id
                )
                self.session.add(belong)
            count += 1

        await self.session.flush()
        return count
