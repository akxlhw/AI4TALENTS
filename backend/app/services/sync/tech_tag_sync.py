"""
Tech tag sync service for creating TalentTechTag records.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import AuthorTechBelong
from app.models.talent import Talent
from app.models.tech_element import TalentTechTag, TechDirection

logger = logging.getLogger(__name__)


class TechTagSyncService:
    """Service for synchronizing tech tags to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_talent_tech_tags(
        self,
        talent: Talent,
        belongs: list[AuthorTechBelong],
        default_tech_direction_id: int | None = None
    ) -> int:
        """
        Create TalentTechTag records based on AuthorTechBelong

        Args:
            talent: Talent object
            belongs: List of AuthorTechBelong records
            default_tech_direction_id: Default tech direction ID

        Returns:
            int: Number of tags created
        """
        created_count = 0

        for belong in belongs:
            # Check if tag already exists
            existing = await self.session.execute(
                select(TalentTechTag).where(
                    TalentTechTag.talent_id == talent.talent_id,
                    TalentTechTag.tech_element_id == belong.tech_element_id
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Get or use default tech direction
            tech_direction_id = await self._get_tech_direction_id(
                belong.tech_element_id,
                default_tech_direction_id
            )

            if not tech_direction_id:
                logger.warning(
                    f"No tech direction found for tech_element_id={belong.tech_element_id}, "
                    f"skipping tag for talent {talent.talent_id}"
                )
                continue

            # Create new tech tag
            new_tag = TalentTechTag(
                talent_id=talent.talent_id,
                tech_element_id=belong.tech_element_id,
                tech_direction_id=tech_direction_id,
                tag_level="primary",
                tag_source="auto_mapping",
                confirm_status="auto_identified",
                confidence_score=min(1.0, belong.work_count_in_venue / 10.0) if belong.work_count_in_venue else 0.5,
                is_enabled=True,
            )

            self.session.add(new_tag)
            created_count += 1

        if created_count > 0:
            await self.session.flush()
            logger.info(f"Created {created_count} tech tags for talent {talent.talent_id}")

        return created_count

    async def _get_tech_direction_id(
        self,
        tech_element_id: int,
        default_id: int | None = None
    ) -> int | None:
        """Get tech direction ID for a tech element"""
        if default_id:
            return default_id

        # Try to get the first tech direction for this tech element
        result = await self.session.execute(
            select(TechDirection).where(
                TechDirection.tech_element_id == tech_element_id,
                TechDirection.is_enabled.is_(True)
            ).order_by(TechDirection.sort_order)
        )
        direction = result.scalar_one_or_none()
        return direction.tech_direction_id if direction else None
