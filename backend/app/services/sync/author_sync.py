"""
Author sync service for synchronizing StdAuthor to Talent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

# Python 3.10 compatibility
UTC = timezone.utc

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VisibilityStatus
from app.models.school import School
from app.models.standardized import StdAuthor
from app.models.talent import RoleProfile, Talent
from app.services.common.cs_concepts import CS_SCORE_THRESHOLD
from app.services.role_identifier import RoleIdentifier

logger = logging.getLogger(__name__)

# Log module load to verify code version
logger.info(f"[AUTHOR_SYNC] Module loaded. CS_SCORE_THRESHOLD: {CS_SCORE_THRESHOLD}")


class AuthorSyncService:
    """Service for synchronizing standardized authors to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_author_to_talent(
        self,
        std_author: StdAuthor,
        update_existing: bool = True
    ) -> tuple[Talent | None, bool]:
        """
        Sync standardized author to serving layer Talent table

        Args:
            std_author: Standardized author object
            update_existing: Whether to update existing records

        Returns:
            Tuple[Optional[Talent], bool]: (Talent object or None, is_new)
            Returns (None, False) if author's CS score is below threshold
        """
        # Filter non-CS background authors
        # Handle None value as 0.0 (filtered)
        cs_score = std_author.cs_concepts_score or 0.0
        if cs_score < CS_SCORE_THRESHOLD:
            logger.debug(
                f"[CS_FILTER] Skipping {std_author.name_normalized}: "
                f"CS score {cs_score:.2f} < {CS_SCORE_THRESHOLD}"
            )
            return None, False

        logger.debug(f"[CS_PASS] {std_author.name_normalized}: CS score {cs_score:.2f}")

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

        logger.debug(
            f"Created talent: {new_talent.talent_id} - {new_talent.name} "
            f"(role: {role_result.role_type}, confidence: {role_result.confidence})"
        )

        return new_talent, True

    async def _get_school_id(self, std_author: StdAuthor) -> int | None:
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
        school_id: int | None
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
        school_id: int | None
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

    async def _update_role_profile(self, talent: Talent, role_result) -> RoleProfile | None:
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
