"""
Author sync service for synchronizing StdAuthor to Talent.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.standardized import StdAuthor
from app.models.talent import Talent, RoleProfile
from app.models.school import School
from app.models.enums import VisibilityStatus
from app.services.role_identifier import RoleIdentifier

logger = logging.getLogger(__name__)


class AuthorSyncService:
    """Service for synchronizing standardized authors to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_author_to_talent(
        self,
        std_author: StdAuthor,
        update_existing: bool = True
    ) -> Tuple[Talent, bool]:
        """
        Sync standardized author to serving layer Talent table

        Args:
            std_author: Standardized author object
            update_existing: Whether to update existing records

        Returns:
            Tuple[Talent, bool]: (Talent object, is_new)
        """
        # 1. Find existing Talent by source ID
        result = await self.session.execute(
            select(Talent).where(
                Talent.source_record_id == std_author.openalex_author_id
            )
        )
        existing_talent = result.scalar_one_or_none()

        # 2. Role identification
        role_result = RoleIdentifier.identify(
            works_count=std_author.works_count or 0,
            cited_by_count=std_author.cited_by_count or 0,
            h_index=std_author.h_index or 0
        )

        # 3. Get or create school association
        school_id = await self._get_school_id(std_author)

        if existing_talent:
            # Update existing record
            if update_existing:
                await self._update_talent(existing_talent, std_author, role_result, school_id)

            await self.session.flush()
            return existing_talent, False

        # 4. Create new Talent
        new_talent = await self._create_talent(std_author, role_result, school_id)

        logger.info(
            f"Created talent: {new_talent.talent_id} - {new_talent.name} "
            f"(role: {role_result.role_type}, confidence: {role_result.confidence})"
        )

        return new_talent, True

    async def _get_school_id(self, std_author: StdAuthor) -> Optional[int]:
        """Get school ID for author"""
        if not std_author.std_school_id:
            return None

        # Find associated serving layer school
        if std_author.school:
            school_result = await self.session.execute(
                select(School).where(
                    School.source_record_id == std_author.school.openalex_institution_id
                )
            )
            school = school_result.scalar_one_or_none()
            if school:
                return school.school_id

        return None

    async def _update_talent(
        self,
        talent: Talent,
        std_author: StdAuthor,
        role_result,
        school_id: Optional[int]
    ):
        """Update existing talent record"""
        talent.name = std_author.name_normalized
        talent.name_en = std_author.name_original
        talent.orcid = std_author.orcid
        talent.std_author_id = std_author.std_author_id
        talent.school_id = school_id
        talent.role_type = role_result.role_type
        talent.role_confidence = role_result.confidence
        talent.works_count = std_author.works_count or 0
        talent.cited_by_count = std_author.cited_by_count or 0
        talent.h_index = std_author.h_index or 0
        talent.openalex_topics = std_author.openalex_topics or []
        talent.source_type = "openalex"
        talent.source_record_id = std_author.openalex_author_id

        # Update role profile
        await self._update_role_profile(talent, role_result)

    async def _create_talent(
        self,
        std_author: StdAuthor,
        role_result,
        school_id: Optional[int]
    ) -> Talent:
        """Create new talent record"""
        new_talent = Talent(
            std_author_id=std_author.std_author_id,
            source_type="openalex",
            source_record_id=std_author.openalex_author_id,
            name=std_author.name_normalized,
            name_en=std_author.name_original,
            orcid=std_author.orcid,
            school_id=school_id,
            role_type=role_result.role_type,
            role_confidence=role_result.confidence,
            works_count=std_author.works_count or 0,
            cited_by_count=std_author.cited_by_count or 0,
            h_index=std_author.h_index or 0,
            openalex_topics=std_author.openalex_topics or [],
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )

        self.session.add(new_talent)
        await self.session.flush()

        # Create role profile
        await self._create_role_profile(new_talent, role_result)

        return new_talent

    async def _create_role_profile(self, talent: Talent, role_result) -> RoleProfile:
        """Create role profile"""
        profile = RoleProfile(
            talent_id=talent.talent_id,
            role_type=role_result.role_type,
            role_confidence=role_result.confidence,
            role_reason=role_result.reason,
            identification_method="heuristic",
            identified_at=datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def _update_role_profile(self, talent: Talent, role_result) -> Optional[RoleProfile]:
        """Update role profile"""
        result = await self.session.execute(
            select(RoleProfile).where(RoleProfile.talent_id == talent.talent_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            profile.role_type = role_result.role_type
            profile.role_confidence = role_result.confidence
            profile.role_reason = role_result.reason
            profile.identification_method = "heuristic"
            profile.identified_at = datetime.now(timezone.utc).isoformat()
        else:
            profile = await self._create_role_profile(talent, role_result)

        return profile
