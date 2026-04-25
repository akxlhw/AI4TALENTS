"""
Tech tag sync service for creating TalentTechTag records.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import AuthorTechBelong
from app.models.talent import Talent
from app.models.tech_domain import TalentTechTag, TechDirection

logger = logging.getLogger(__name__)


class TechTagSyncService:
    """Service for synchronizing tech tags to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_talent_tech_tags(
        self,
        talent: Talent,
        belongs: list[AuthorTechBelong],
        default_tech_direction_id: int | None = None,
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
        if not belongs:
            return 0

        created_count = 0

        # Batch check existing tags - get all domain IDs for this talent at once
        domain_ids = [b.tech_domain_id for b in belongs]
        existing_result = await self.session.execute(
            select(TalentTechTag.tech_domain_id).where(
                TalentTechTag.talent_id == talent.talent_id,
                TalentTechTag.tech_domain_id.in_(domain_ids),
            )
        )
        existing_domain_ids = {row.tech_domain_id for row in existing_result.all()}

        # Pre-fetch tech directions for all domains to avoid N+1 in _get_tech_direction_id
        domain_ids_needing_direction = [
            b.tech_domain_id for b in belongs if b.tech_domain_id not in existing_domain_ids
        ]
        if domain_ids_needing_direction:
            directions_result = await self.session.execute(
                select(TechDirection)
                .where(
                    TechDirection.tech_domain_id.in_(domain_ids_needing_direction),
                    TechDirection.is_enabled.is_(True),
                )
                .order_by(TechDirection.tech_domain_id, TechDirection.sort_order)
            )
            # Build a map: tech_domain_id -> first tech_direction_id
            self._direction_map: dict[int, int] = {}
            for direction in directions_result.scalars().all():
                if direction.tech_domain_id not in self._direction_map:
                    self._direction_map[direction.tech_domain_id] = direction.tech_direction_id
        else:
            self._direction_map = {}

        for belong in belongs:
            # Check if tag already exists (using batch-fetched data)
            if belong.tech_domain_id in existing_domain_ids:
                continue

            # Get tech direction from pre-fetched map or use default
            if default_tech_direction_id:
                tech_direction_id = default_tech_direction_id
            else:
                tech_direction_id = self._direction_map.get(belong.tech_domain_id)

            if not tech_direction_id:
                logger.warning(
                    f"No tech direction found for tech_domain_id={belong.tech_domain_id}, "
                    f"skipping tag for talent {talent.talent_id}"
                )
                continue

            # Create new tech tag
            new_tag = TalentTechTag(
                talent_id=talent.talent_id,
                tech_domain_id=belong.tech_domain_id,
                tech_direction_id=tech_direction_id,
                tag_level="primary",
                tag_source="auto_mapping",
                confirm_status="auto_identified",
                confidence_score=(
                    min(1.0, belong.work_count_in_venue / 10.0)
                    if belong.work_count_in_venue
                    else 0.5
                ),
                is_enabled=True,
            )

            self.session.add(new_tag)
            created_count += 1

        if created_count > 0:
            await self.session.flush()
            logger.info(f"Created {created_count} tech tags for talent {talent.talent_id}")

        return created_count

    async def _get_tech_direction_id(
        self, tech_domain_id: int, default_id: int | None = None
    ) -> int | None:
        """Get tech direction ID for a tech domain"""
        if default_id:
            return default_id

        # Try to get the first tech direction for this tech domain
        result = await self.session.execute(
            select(TechDirection)
            .where(
                TechDirection.tech_domain_id == tech_domain_id, TechDirection.is_enabled.is_(True)
            )
            .order_by(TechDirection.sort_order)
        )
        direction = result.scalar_one_or_none()
        return direction.tech_direction_id if direction else None
